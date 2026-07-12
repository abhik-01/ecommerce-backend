from .models import Payment, Transaction
from django.db import transaction as db_transaction
from payments.gateways.stripe_gateway import StripeAdapter
from payments.gateways.razorpay_gateway import RazorpayAdapter
from .kafka_producer import publish_payment_completed, publish_payment_failed


class PaymentService:
    def get_payment_adapter(self, gateway_name=None):
        """
        Returns the healthy payment gateway adapter for the given gateway_name.
        If gateway_name is None, returns the first healthy adapter found.
        """
        adapters = {
            'stripe': StripeAdapter(),
            'razorpay': RazorpayAdapter(),
        }
        if gateway_name:
            adapter = adapters.get(gateway_name.lower())
            if adapter and adapter.check_health():
                return adapter
            raise RuntimeError(f"No healthy payment gateway available for: {gateway_name}")
        for adapter in adapters.values():
            if adapter.check_health():
                return adapter
        raise RuntimeError("No healthy payment gateway available")

    def initiate_checkout_payment(self, data, success_url):
        if not success_url:
            return {
                'error': 'success_url required.'
            }
        adapter = RazorpayAdapter()
        result = adapter.create_checkout_session(
            amount=data['amount'],
            currency=data.get('currency', 'INR'),
            order_id=data['order_id'],
            quantity=data.get('quantity', 1),
            metadata=data.get('metadata', {}),
            success_url=success_url,
            cancel_url=f"http://localhost:8000/api/payments/cancel/?session_id={{CHECKOUT_SESSION_ID}}&order_id={data['order_id']}"
        )
        if result.get('error'):
            return {
                'error': result['error']
            }
        session_id = result.get('session_id')
        redirect_url = result.get('redirect_url')
        with db_transaction.atomic():
            receipt_url = None
            # Try to extract receipt_url from gateway response
            gateway_resp = result.get('gateway_response')
            if gateway_resp:
                # Stripe: session object does not have receipt_url, but charge object does (from webhook)
                receipt_url = gateway_resp.get('receipt_url')
            payment = Payment.objects.create(
                amount=data['amount'],
                quantity=data.get('quantity', 1),
                currency=data.get('currency', 'INR'),
                gateway=adapter.__class__.__name__.replace('Adapter', '').lower(),
                order_id=data['order_id'],
                status='pending',
                metadata=data.get('metadata', {}),
                session_id=session_id
            )
            Transaction.objects.create(
                payment=payment,
                type='payment',
                amount=data['amount'],
                currency=data.get('currency', 'INR'),
                status='pending',
                transaction_id=None,
                gateway_response=result,
                session_id=session_id,
                receipt_url=receipt_url
            )
        return {
            'payment_id': payment.id,
            'order_id': payment.order_id,
            'status': payment.status,
            'redirect_url': redirect_url,
            'session_id': session_id,
            'transaction_id': None
        }

    def handle_webhook(self, request, gateway_name):
        if gateway_name == 'stripe':
            adapter = StripeAdapter()
        elif gateway_name == 'razorpay':
            adapter = RazorpayAdapter()
        else:
            return {'error': 'Unsupported gateway', 'status': 400}
        result = adapter.process_webhook_event(request)
        if result.get('error'):
            return {'error': result['error'], 'status': result.get('status', 400)}

        print(result)
        print('******')


        session_id = result.get('session_id')
        transaction_id = result.get('transaction_id')
        event_type = result.get('event_type')
        status_map = {
            'checkout.session.completed': ('completed', 'success'),
            'payment_intent.succeeded': ('completed', 'success'),
            'payment_intent.payment_failed': ('failed', 'failed'),
            'charge.succeeded': (None, 'success'),
            'charge.updated': (None, None),
            'checkout.session.expired': ('failed', 'failed'),
            'payment_link.paid': ('completed', 'success'),
            'payment.failed': ('failed', 'failed')
        }
        payment_status, transaction_status = status_map.get(event_type, (None, None))
        txn = None
        if session_id:
            txn = Transaction.objects.filter(session_id=session_id).first()
        if not txn and transaction_id:
            txn = Transaction.objects.filter(transaction_id=transaction_id).first()
        if txn:
            if transaction_id and not txn.transaction_id:
                txn.transaction_id = transaction_id
            if transaction_status:
                txn.status = transaction_status
            txn.save()
            payment = txn.payment
            if payment_status:
                payment.status = payment_status
            # Refund handling (charge.updated)
            if event_type == 'charge.updated':
                charge_obj = result.get('charge_obj')
                if charge_obj and charge_obj.get('status') == 'refunded':
                    payment.status = 'refunded'
                    txn.status = 'success'
                    txn.save()
            # Update receipt_url from charge_obj if present
            charge_obj = result.get('charge_obj')
            if charge_obj:
                receipt_url = charge_obj.get('receipt_url')
                if receipt_url:
                    txn.receipt_url = receipt_url
                    txn.save(update_fields=['receipt_url'])
            payment.save()
            if payment.status == 'completed':
                publish_payment_completed(
                    payment_id=payment.id,
                    order_id=payment.order_id,
                    amount=str(payment.amount),
                    currency=payment.currency,
                )
            elif payment.status == 'failed':
                publish_payment_failed(
                    payment_id=payment.id,
                    order_id=payment.order_id,
                )
            return {'detail': f'Transaction and Payment updated for event {event_type}.', 'status': 200}
        # Refund event handling
        if event_type in ['charge.refunded', 'refund.succeeded', 'refund.failed']:
            refund_id = result.get('refund_id')
            refund_status = result.get('refund_status')
            gateway_resp = result.get('raw_event', {}).get('data', {}).get('object', {})
            receipt_url = gateway_resp.get('receipt_url')
            refund_txn = None
            if refund_id:
                refund_txn = Transaction.objects.filter(type='refund', transaction_id=refund_id).first()
            if refund_txn:
                if receipt_url:
                    refund_txn.receipt_url = receipt_url
                    refund_txn.save(update_fields=['receipt_url'])
                if refund_status in ['succeeded', 'completed']:
                    refund_txn.status = 'success'
                    refund_txn.save()
                elif refund_status == 'failed':
                    refund_txn.status = 'failed'
                    refund_txn.save()
                return {'detail': f'Refund transaction updated for event {event_type}.', 'status': 200, 'receipt_url': receipt_url}
            else:
                return {'error': 'Refund transaction not found.', 'status': 404}
        else:
            return {'error': 'Transaction not found.', 'status': 404}

    def cancel_payment(self, session_id):
        if not session_id:
            return {'error': 'session_id is required for cancellation.'}
        # Determine gateway from parameter or Payment object
        payment = Payment.objects.filter(session_id=session_id).first()
        if not payment:
            return {'error': 'Unable to determine gateway for cancellation.'}
        gateway_name = payment.gateway
        adapter = self.get_payment_adapter(gateway_name)
        gateway_result = adapter.cancel_payment(session_id)
        if gateway_result.get('error'):
            return gateway_result

        with db_transaction.atomic():
            payment.status = 'failed'
            payment.save()
            Transaction.objects.filter(session_id=session_id).update(status='failed')
        return {'detail': 'Session expired and all related transactions canceled.'}

    def refund_payment(self, payment_id, amount=None):
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return {'error': 'Payment not found', 'status': 404}
        adapter = self.get_payment_adapter(payment.gateway)
        transaction_obj = payment.latest_transaction()
        gateway_transaction_id = transaction_obj.transaction_id if transaction_obj else payment.session_id
        result = adapter.refund_payment(gateway_transaction_id, amount)
        with db_transaction.atomic():
            refund_status = 'pending'
            receipt_url = None
            gateway_resp = result.get('gateway_response')
            if gateway_resp:
                receipt_url = gateway_resp.get('receipt_url')
            refund_txn = Transaction.objects.create(
                payment=payment,
                type='refund',
                amount=amount if amount else payment.amount,
                currency=payment.currency,
                status=refund_status,
                transaction_id=result.get('refund_id'),
                gateway_response=result,
                session_id=payment.session_id,
                receipt_url=receipt_url
            )
            payment.status = 'pending'
            payment.save(update_fields=['status'])
        return {
            'payment_id': payment.id,
            'refund_status': refund_status,
            'refund_id': result.get('refund_id'),
            'gateway_response': result.get('gateway_response'),
            'receipt_url': refund_txn.receipt_url
        }

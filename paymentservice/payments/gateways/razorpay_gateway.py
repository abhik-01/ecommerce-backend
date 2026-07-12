import json
import razorpay
from django.conf import settings
from payments.gateways import PaymentGatewayAdapter


class RazorpayAdapter(PaymentGatewayAdapter):
    def __init__(self):
        self.client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    def create_checkout_session(self, amount, currency, order_id, quantity, metadata=None, success_url=None, cancel_url=None):
        try:
            razorpay_amount = int(float(amount) * 100)
            payment_link_data = {
                "amount": razorpay_amount,
                "currency": currency,
                "description": f"Order {order_id} payment",
                "reference_id": order_id,
                "callback_url": success_url,
                "callback_method": "get"
            }
            link = self.client.payment_link.create(payment_link_data)
            return {
                "session_id": link["id"],
                "redirect_url": link["short_url"],
                "status": link["status"],
                "gateway_response": link
            }
        except Exception as e:
            return {"error": str(e)}

    def refund_payment(self, payment_id, amount=None, **kwargs):
        try:
            params = {}
            if amount:
                params['amount'] = int(float(amount) * 100)
            refund = self.client.payment.refund(payment_id, params)
            return {
                'refund_id': refund['id'],
                'status': refund['status'],
                'gateway_response': refund,
                'receipt_url': refund.get('receipt')
            }
        except Exception as e:
            return {'error': str(e), 'status': 'failed'}

    def check_health(self):
        try:
            # Use orders.all() as a health check
            self.client.order.all()
            return True
        except Exception:
            return False

    def process_webhook_event(self, request):
        payload = request.body
        try:
            event = json.loads(payload)
        except Exception:
            return {'status': 400, 'error': 'Invalid payload'}
        event_type = event.get('event')
        session_id = None
        transaction_id = None
        refund_id = None
        refund_status = None
        receipt_url = None
        if event_type == 'payment.captured':
            payment_obj = event['payload']['payment']['entity']
            transaction_id = payment_obj.get('order_id')
            session_id = payment_obj.get('id')
            receipt_url = payment_obj.get('receipt')
        elif event_type == 'payment.failed':
            payment_obj = event['payload']['payment']['entity']
            transaction_id = payment_obj.get('order_id')
            session_id = 'plink_' + payment_obj.get('description').replace('#', '').strip()
        elif event_type == 'order.paid':
            order_obj = event['payload']['order']['entity']
            session_id = order_obj.get('id')
            transaction_id = order_obj.get('order_id')
        elif event_type == 'payment_link.paid':
            payment_link_obj = event['payload']['payment_link']['entity']
            session_id = payment_link_obj.get('id')
            transaction_id = payment_link_obj.get('order_id')
            receipt_url = payment_link_obj.get('receipt')
        elif event_type == 'refund.processed':
            refund_obj = event['payload']['refund']['entity']
            refund_id = refund_obj.get('id')
            refund_status = refund_obj.get('status')
            receipt_url = refund_obj.get('receipt')
        elif event_type == 'refund.failed':
            refund_obj = event['payload']['refund']['entity']
            refund_id = refund_obj.get('id')
            refund_status = refund_obj.get('status')
        return {
            'session_id': session_id,
            'transaction_id': transaction_id,
            'event_type': event_type,
            'refund_id': refund_id,
            'refund_status': refund_status,
            'receipt_url': receipt_url,
            'raw_event': event
        }

    def cancel_payment(self, session_id):
        try:
            # Razorpay does not support direct order cancellation via API, so we simulate
            # You may want to update order status in your DB or notify frontend
            return {'detail': 'Razorpay order cancellation simulated.'}
        except Exception as e:
            return {'error': str(e)}

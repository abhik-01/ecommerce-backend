import stripe
from django.conf import settings
from payments.gateways import PaymentGatewayAdapter


class StripeAdapter(PaymentGatewayAdapter):
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def refund_payment(self, payment_id, amount=None, **kwargs):
        try:
            params = {'payment_intent': payment_id}
            if amount:
                params['amount'] = int(float(amount) * 100)
            refund = stripe.Refund.create(**params)
            return {
                'refund_id': refund.id,
                'status': refund.status,
                'gateway_response': refund
            }
        except Exception as e:
            return {'error': str(e), 'status': 'failed'}

    def check_health(self):
        try:
            stripe.Balance.retrieve()
            return True
        except Exception:
            return False

    def process_webhook_event(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        event = None
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            return {'session_id': None, 'transaction_id': None, 'event_type': None, 'status': 400, 'error': 'Invalid payload'}
        except stripe.error.SignatureVerificationError:
            return {'session_id': None, 'transaction_id': None, 'event_type': None, 'status': 400, 'error': 'Invalid signature'}

        event_type = event.get('type')
        session_id = None
        transaction_id = None
        charge_obj = None
        refund_id = None
        refund_status = None
        # Handle the event
        if event_type == 'payment_intent.succeeded':
            intent = event['data']['object']
            transaction_id = intent.get('id')
        elif event_type == 'payment_intent.payment_failed':
            intent = event['data']['object']
            transaction_id = intent.get('id')
        elif event_type == 'checkout.session.completed':
            session = event['data']['object']
            session_id = session.get('id')
            transaction_id = session.get('payment_intent')
        elif event_type == 'charge.succeeded':
            charge_obj = event['data']['object']
            transaction_id = charge_obj.get('payment_intent')
        elif event_type == 'charge.updated':
            charge_obj = event['data']['object']
            transaction_id = charge_obj.get('payment_intent')
        elif event_type == 'charge.refunded':
            charge_obj = event['data']['object']
            transaction_id = charge_obj.get('payment_intent')
            refunds = charge_obj.get('refunds', {}).get('data', [])
            if refunds:
                refund_id = refunds[-1].get('id')
                refund_status = refunds[-1].get('status')
        elif event_type in ['refund.succeeded', 'refund.failed']:
            refund_obj = event['data']['object']
            refund_id = refund_obj.get('id')
            refund_status = refund_obj.get('status')
            transaction_id = refund_obj.get('payment_intent')
        return {
            'session_id': session_id,
            'transaction_id': transaction_id,
            'event_type': event_type,
            'refund_id': refund_id,
            'refund_status': refund_status,
            'charge_obj': charge_obj,
            'raw_event': event
        }

    def create_checkout_session(self, amount, currency, order_id, quantity, metadata=None, success_url=None, cancel_url=None):
        try:
            stripe_amount = int(float(amount) * 100)
            metadata = metadata or {}
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': f"Order {order_id} payment",
                        },
                        'unit_amount': stripe_amount,
                    },
                    'quantity': quantity,
                }],
                mode='payment',
                metadata={**metadata, 'order_id': order_id},
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return {
                'session_id': session.id,
                'redirect_url': session.url,
                'status': session.status,
                'gateway_response': session
            }
        except Exception as e:
            return {'error': str(e)}

    def cancel_payment(self, session_id):
        try:
            stripe.checkout.Session.expire(session_id)
            return {'detail': 'Stripe session expired.'}
        except Exception as e:
            return {'error': str(e)}

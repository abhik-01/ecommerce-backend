from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from payments.models import Payment, Transaction


class TestPaymentModel(TestCase):
    def test_create_payment(self):
        payment = Payment.objects.create(
            amount=Decimal('500.00'),
            currency='INR',
            status='pending',
            gateway='razorpay',
            order_id='order_001',
        )
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.gateway, 'razorpay')
        self.assertIn('razorpay', str(payment))

    def test_create_transaction(self):
        payment = Payment.objects.create(
            amount=Decimal('500.00'),
            gateway='stripe',
            order_id='order_002',
        )
        txn = Transaction.objects.create(
            payment=payment,
            type='payment',
            amount=Decimal('500.00'),
            status='pending',
        )
        self.assertEqual(txn.payment, payment)
        self.assertEqual(payment.transactions.count(), 1)

    def test_latest_transaction(self):
        payment = Payment.objects.create(
            amount=Decimal('500.00'),
            gateway='stripe',
            order_id='order_003',
        )
        t1 = Transaction.objects.create(payment=payment, type='payment', amount=Decimal('500.00'))
        t2 = Transaction.objects.create(payment=payment, type='refund', amount=Decimal('500.00'))
        self.assertEqual(payment.latest_transaction().id, t2.id)

    def test_payment_status_choices(self):
        for s in ['pending', 'completed', 'failed', 'refunded']:
            p = Payment.objects.create(
                amount=Decimal('100.00'), gateway='stripe',
                order_id=f'order_{s}', status=s,
            )
            self.assertEqual(p.status, s)


class TestPaymentServiceInitiate(TestCase):
    @patch('payments.services.RazorpayAdapter')
    def test_initiate_payment_success(self, MockAdapter):
        instance = MockAdapter.return_value
        instance.create_checkout_session.return_value = {
            'session_id': 'sess_123',
            'redirect_url': 'http://pay.example.com',
            'gateway_response': {},
        }
        from payments.services import PaymentService
        svc = PaymentService()
        result = svc.initiate_checkout_payment(
            data={'amount': Decimal('500.00'), 'order_id': 'order_001', 'currency': 'INR'},
            success_url='http://success.example.com',
        )
        self.assertIn('payment_id', result)
        self.assertEqual(result['session_id'], 'sess_123')

    def test_initiate_payment_missing_success_url(self):
        from payments.services import PaymentService
        result = PaymentService().initiate_checkout_payment(
            data={'amount': 500, 'order_id': 'order_001'},
            success_url='',
        )
        self.assertIn('error', result)


class TestPaymentViews(TestCase):
    def setUp(self):
        self.client = APIClient()
        import jwt
        from django.conf import settings
        token = jwt.encode(
            {'user_id': 1, 'email': 'test@example.com', 'role': 'user'},
            settings.JWT_SECRET_KEY, algorithm='HS256',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_payment_status_missing_param(self):
        response = self.client.get('/api/payments/status/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payment_status_not_found(self):
        response = self.client.get('/api/payments/status/?session_id=nonexistent_session')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_missing_session(self):
        response = self.client.get('/api/payments/cancel/')
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND])

    @patch('payments.services.PaymentService.refund_payment')
    def test_refund_not_found(self, mock_refund):
        mock_refund.return_value = {'error': 'Payment not found', 'status': 404}
        response = self.client.post('/api/payments/refund/', {'payment_id': 99999}, format='json')
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST])

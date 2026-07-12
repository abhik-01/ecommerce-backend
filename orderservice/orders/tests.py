from unittest.mock import patch
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from orders.models import Order, OrderItem, OrderTracking
from orders.services import OrderService
from orders.kafka_consumer import handle_payment_completed, handle_payment_failed


class TestOrderModel(TestCase):
    def test_create_order(self):
        order = Order.objects.create(
            user_id=1,
            status='PENDING',
            total_amount=Decimal('500.00'),
        )
        self.assertEqual(order.user_id, 1)
        self.assertEqual(order.status, 'PENDING')
        self.assertEqual(order.delivery_status, 'NOT_SHIPPED')

    def test_order_str(self):
        order = Order.objects.create(user_id=2, total_amount=Decimal('100.00'))
        self.assertIn(str(order.id), str(order))

    def test_order_item_creation(self):
        order = Order.objects.create(user_id=1, total_amount=Decimal('200.00'))
        item = OrderItem.objects.create(
            order=order,
            product_id=5,
            quantity=2,
            price=Decimal('100.00'),
        )
        self.assertEqual(item.order, order)
        self.assertEqual(item.quantity, 2)

    def test_order_tracking_creation(self):
        order = Order.objects.create(user_id=1, total_amount=Decimal('300.00'))
        tracking = OrderTracking.objects.create(
            order=order,
            status='IN_TRANSIT',
            location='Mumbai Hub',
        )
        self.assertEqual(tracking.status, 'IN_TRANSIT')
        self.assertEqual(tracking.location, 'Mumbai Hub')


class TestOrderService(TestCase):
    @patch('orders.services.publish_order_created')
    def test_create_order_publishes_kafka(self, mock_publish):
        items = [{'product_id': 1, 'quantity': 2, 'price': '100.00'}]
        order = OrderService.create_order(user_id=1, items=items, total_amount='200.00')
        self.assertEqual(order.status, 'CONFIRMED')
        self.assertEqual(order.user_id, 1)
        mock_publish.assert_called_once()
        created_items = list(order.items.all())
        self.assertEqual(len(created_items), 1)

    def test_get_order_history(self):
        Order.objects.create(user_id=1, total_amount=Decimal('100.00'))
        Order.objects.create(user_id=1, total_amount=Decimal('200.00'))
        Order.objects.create(user_id=2, total_amount=Decimal('300.00'))
        orders = OrderService.get_order_history(user_id=1)
        self.assertEqual(orders.count(), 2)

    @patch('orders.services.publish_order_status_updated')
    def test_update_delivery_status(self, mock_publish):
        order = Order.objects.create(user_id=1, total_amount=Decimal('100.00'))
        tracking = OrderService.update_delivery_status(
            order_id=order.id, status='IN_TRANSIT', location='Delhi'
        )
        self.assertEqual(tracking.status, 'IN_TRANSIT')
        mock_publish.assert_called_once()

    def test_get_order_tracking(self):
        order = Order.objects.create(user_id=1, total_amount=Decimal('100.00'))
        OrderTracking.objects.create(order=order, status='NOT_SHIPPED')
        OrderTracking.objects.create(order=order, status='IN_TRANSIT')
        tracking_qs = OrderService.get_order_tracking(order.id)
        self.assertEqual(tracking_qs.count(), 2)


class TestPaymentEventConsumer(TestCase):
    def test_payment_completed_confirms_order(self):
        order = Order.objects.create(user_id=1, total_amount=Decimal('100.00'), status='PENDING')
        handle_payment_completed({'order_id': order.id, 'payment_id': 555})
        order.refresh_from_db()
        self.assertEqual(order.status, 'CONFIRMED')
        self.assertEqual(order.payment_id, 555)

    def test_payment_failed_cancels_order(self):
        order = Order.objects.create(user_id=1, total_amount=Decimal('100.00'), status='PENDING')
        handle_payment_failed({'order_id': order.id, 'reason': 'declined'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'CANCELLED')

    def test_payment_completed_unknown_order_is_noop(self):
        # Should not raise even if the order_id does not exist
        handle_payment_completed({'order_id': 999999, 'payment_id': 1})


class TestOrderViewSet(TestCase):
    def setUp(self):
        self.client = APIClient()
        import jwt
        from django.conf import settings
        token = jwt.encode(
            {'user_id': 1, 'email': 'test@example.com', 'role': 'user'},
            settings.JWT_SECRET_KEY, algorithm='HS256',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    @patch('orders.services.publish_order_created')
    def test_create_order(self, mock_publish):
        payload = {
            'items': [{'product_id': 1, 'quantity': 1, 'price': '99.99'}],
            'total_amount': '99.99',
        }
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'CONFIRMED')

    def test_create_order_unauthenticated(self):
        client = APIClient()  # no token
        response = client.post('/api/orders/', {
            'items': [{'product_id': 1, 'quantity': 1, 'price': '99.99'}],
            'total_amount': '99.99',
        }, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN,
        ])

    @patch('orders.services.publish_order_created')
    def test_list_orders(self, mock_publish):
        OrderService.create_order(user_id=1, items=[{'product_id': 1, 'quantity': 1, 'price': '50.00'}], total_amount='50.00')
        response = self.client.get('/api/orders/?user_id=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('orders.services.publish_order_created')
    def test_retrieve_order(self, mock_publish):
        order = OrderService.create_order(user_id=1, items=[{'product_id': 1, 'quantity': 1, 'price': '50.00'}], total_amount='50.00')
        response = self.client.get(f'/api/orders/{order.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], order.id)

    def test_create_order_missing_items(self):
        response = self.client.post('/api/orders/', {'total_amount': '50.00'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('orders.services.publish_order_created')
    def test_order_tracking(self, mock_publish):
        order = OrderService.create_order(user_id=1, items=[{'product_id': 1, 'quantity': 1, 'price': '50.00'}], total_amount='50.00')
        response = self.client.get(f'/api/orders/{order.id}/tracking/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

import json
import mongomock
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


def _connect_mongo():
    import mongoengine
    import mongoengine.connection as _mc
    if 'default' in _mc._connections:
        mongoengine.disconnect(alias='default')
    mongoengine.connect('testdb', mongo_client_class=mongomock.MongoClient, alias='default')


def _disconnect_mongo():
    import mongoengine
    mongoengine.disconnect(alias='default')


class TestCartServiceAddToCart(TestCase):
    def setUp(self):
        _connect_mongo()

    def tearDown(self):
        from cart.models import Cart
        Cart.objects.all().delete()
        _disconnect_mongo()

    @patch('cart.services._store_in_cache')
    def test_add_new_item_creates_cart(self, mock_cache):
        from cart.services import CartService
        svc = CartService()
        cart = svc.add_to_cart('user1', {'product_id': '10', 'name': 'Widget', 'price': 100.0}, 2)
        self.assertEqual(len(cart.items), 1)
        self.assertEqual(cart.items[0].product_id, '10')
        self.assertEqual(cart.items[0].quantity, 2)
        mock_cache.assert_called_once()

    @patch('cart.services._store_in_cache')
    def test_add_existing_item_increments_quantity(self, mock_cache):
        from cart.services import CartService
        svc = CartService()
        svc.add_to_cart('user2', {'product_id': '5', 'name': 'Pen', 'price': 10.0}, 1)
        cart = svc.add_to_cart('user2', {'product_id': '5', 'name': 'Pen', 'price': 10.0}, 3)
        self.assertEqual(len(cart.items), 1)
        self.assertEqual(cart.items[0].quantity, 4)

    @patch('cart.services._store_in_cache')
    def test_remove_item_from_cart(self, mock_cache):
        from cart.services import CartService
        svc = CartService()
        svc.add_to_cart('user3', {'product_id': '7', 'name': 'Book', 'price': 200.0}, 1)
        cart = svc.remove_from_cart('user3', '7')
        self.assertEqual(len(cart.items), 0)

    def test_remove_from_nonexistent_cart_returns_none(self):
        from cart.services import CartService
        svc = CartService()
        result = svc.remove_from_cart('ghost_user', '999')
        self.assertIsNone(result)

    @patch('cart.services._store_in_cache')
    def test_update_cart_item_quantity(self, mock_cache):
        from cart.services import CartService
        svc = CartService()
        svc.add_to_cart('user4', {'product_id': '3', 'name': 'Mug', 'price': 50.0}, 1)
        cart = svc.update_cart_item('user4', '3', 5)
        self.assertEqual(cart.items[0].quantity, 5)
        self.assertAlmostEqual(cart.items[0].total, 250.0)


class TestCartServiceReviewCart(TestCase):
    def setUp(self):
        _connect_mongo()

    def tearDown(self):
        from cart.models import Cart
        Cart.objects.all().delete()
        _disconnect_mongo()

    @patch('cart.services._get_from_cache', return_value=None)
    @patch('cart.services._store_in_cache')
    def test_review_cart_returns_total(self, mock_store, mock_get):
        from cart.services import CartService
        svc = CartService()
        svc.add_to_cart('user5', {'product_id': '1', 'name': 'A', 'price': 100.0}, 2)
        result = svc.review_cart('user5')
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['total'], 200.0)

    @patch('cart.services._get_from_cache')
    def test_review_cart_uses_cache_when_available(self, mock_get):
        cached_data = {
            'user_id': 'user6',
            'items': [{'product_id': '9', 'price': 50.0, 'quantity': 2, 'total': 100.0, 'name': 'Item', 'image_url': ''}],
        }
        mock_get.return_value = cached_data
        from cart.services import CartService
        svc = CartService()
        result = svc.review_cart('user6')
        self.assertEqual(result['total'], 100.0)

    @patch('cart.services._get_from_cache', return_value=None)
    def test_review_cart_nonexistent_user_returns_none(self, mock_get):
        from cart.services import CartService
        svc = CartService()
        result = svc.review_cart('nobody')
        self.assertIsNone(result)


class TestCartServiceCheckout(TestCase):
    def setUp(self):
        _connect_mongo()

    def tearDown(self):
        from cart.models import Cart
        Cart.objects.all().delete()
        _disconnect_mongo()

    @patch('cart.services.publish_cart_checkout')
    @patch('cart.services._invalidate_cache')
    @patch('cart.services._store_in_cache')
    def test_checkout_publishes_event_and_invalidates_cache(self, mock_store, mock_invalidate, mock_publish):
        from cart.services import CartService
        svc = CartService()
        svc.add_to_cart('user7', {'product_id': '2', 'name': 'TV', 'price': 5000.0}, 1)
        result = svc.checkout_cart('user7', 'Bangalore', 'razorpay')
        mock_publish.assert_called_once()
        mock_invalidate.assert_called_once_with('user7')
        self.assertIn('cart', result)
        self.assertEqual(result['payment_method'], 'razorpay')

    @patch('cart.services._invalidate_cache')
    def test_checkout_empty_cart_returns_none(self, mock_invalidate):
        from cart.services import CartService
        svc = CartService()
        result = svc.checkout_cart('empty_user', 'address', 'stripe')
        self.assertIsNone(result)


class TestCartViewSet(TestCase):
    def setUp(self):
        self.client = APIClient()
        _connect_mongo()
        self.user_id = 'apiuser1'
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self._make_token(self.user_id)}')

    @staticmethod
    def _make_token(user_id):
        import jwt
        from django.conf import settings
        return jwt.encode(
            {'user_id': user_id, 'email': f'{user_id}@example.com', 'role': 'user'},
            settings.JWT_SECRET_KEY, algorithm='HS256',
        )

    def tearDown(self):
        from cart.models import Cart
        Cart.objects.all().delete()
        _disconnect_mongo()

    @patch('cart.services._store_in_cache')
    def test_add_to_cart_api(self, mock_cache):
        payload = {
            'product_data': {'product_id': '100', 'name': 'Headphones', 'price': 2000.0, 'quantity': 1},
            'quantity': 1,
        }
        response = self.client.post('/cart/add/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)

    def test_add_to_cart_unauthenticated(self):
        client = APIClient()  # no token
        response = client.post('/cart/add/', {
            'product_data': {'product_id': '1', 'name': 'X', 'price': 100.0, 'quantity': 1},
            'quantity': 1,
        }, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN,
        ])

    @patch('cart.services._store_in_cache')
    def test_by_user_cart_not_found(self, mock_cache):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self._make_token("unknown")}')
        with patch('cart.services._get_from_cache', return_value=None):
            response = self.client.get('/cart/by_user/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_by_user_unauthenticated(self):
        client = APIClient()  # no token
        response = client.get('/cart/by_user/')
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN,
        ])

    @patch('cart.services._store_in_cache')
    @patch('cart.services.publish_cart_checkout')
    @patch('cart.services._invalidate_cache')
    def test_checkout_api(self, mock_inv, mock_pub, mock_cache):
        from cart.services import CartService
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self._make_token("apiuser2")}')
        CartService().add_to_cart('apiuser2', {'product_id': '5', 'name': 'Book', 'price': 300.0}, 2)
        response = self.client.post('/cart/checkout/', {
            'address': '123 Main St',
            'payment_method': 'stripe',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('cart', response.data)

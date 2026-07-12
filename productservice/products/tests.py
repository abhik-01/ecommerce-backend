from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from products.models import Product, Category
from products.services import ProductService, CategoryService


class TestCategoryModel(TestCase):
    def test_create_category(self):
        cat = Category.objects.create(name='Electronics', description='All gadgets')
        self.assertEqual(cat.name, 'Electronics')
        self.assertEqual(str(cat), 'Electronics')

    def test_get_or_create_by_name_creates(self):
        cat = Category.get_or_create_by_name('Books')
        self.assertEqual(cat.name, 'Books')

    def test_get_or_create_by_name_returns_existing(self):
        Category.objects.create(name='Clothing')
        cat = Category.get_or_create_by_name('Clothing')
        self.assertEqual(Category.objects.filter(name='Clothing').count(), 1)

    def test_all_products_excludes_deleted(self):
        cat = Category.objects.create(name='Toys')
        Product.objects.create(title='Lego', price=Decimal('50.00'), category=cat)
        Product.objects.create(title='Deleted', price=Decimal('10.00'), category=cat, is_deleted=True)
        self.assertEqual(cat.all_products.count(), 1)


class TestProductModel(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='Sports')

    def test_create_product(self):
        product = Product.objects.create(
            title='Running Shoes',
            description='Fast shoes',
            price=Decimal('2500.00'),
            category=self.cat,
        )
        self.assertEqual(str(product), 'Running Shoes')
        self.assertFalse(product.is_deleted)

    def test_create_with_category(self):
        product = Product.create_with_category(
            title='Football', description='Round ball', price=500.0,
            image_url='', category_name='Sports Goods',
        )
        self.assertEqual(product.category.name, 'Sports Goods')

    def test_soft_delete_not_in_active_queryset(self):
        Product.objects.create(title='SoftDel', price=Decimal('10.00'), category=self.cat, is_deleted=True)
        active = Product.objects.filter(is_deleted=False)
        self.assertFalse(active.filter(title='SoftDel').exists())


class TestProductService(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='TestCat')

    def test_create_product_via_service(self):
        product = ProductService.create_product(
            title='Laptop', description='Good laptop', price=50000.0,
            category_name='TestCat', image_url='',
        )
        self.assertEqual(product.title, 'Laptop')

    def test_get_product_by_id(self):
        p = Product.objects.create(title='Widget', price=Decimal('10.00'), category=self.cat)
        found = ProductService.get_product_by_id(p.id)
        self.assertEqual(found.id, p.id)

    def test_delete_product_soft_deletes(self):
        p = Product.objects.create(title='ToDelete', price=Decimal('10.00'), category=self.cat)
        ProductService.delete_product(p.id)
        p.refresh_from_db()
        self.assertTrue(p.is_deleted)


class TestProductViewSet(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cat = Category.objects.create(name='ViewTest')
        import jwt
        from django.conf import settings
        token = jwt.encode(
            {'user_id': 1, 'email': 'staff@example.com', 'role': 'admin', 'is_staff': True},
            settings.JWT_SECRET_KEY, algorithm='HS256',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_list_products(self):
        Product.objects.create(title='P1', price=Decimal('10.00'), category=self.cat)
        response = self.client.get('/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_products_is_public(self):
        client = APIClient()  # no token
        Product.objects.create(title='P1', price=Decimal('10.00'), category=self.cat)
        response = client.get('/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_product(self):
        response = self.client.post('/products/', {
            'title': 'New Product',
            'description': 'desc',
            'price': '99.99',
            'category': 'ViewTest',
            'image_url': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_product_unauthenticated(self):
        client = APIClient()  # no token
        response = client.post('/products/', {
            'title': 'Blocked', 'description': 'd', 'price': '9.99',
            'category': 'ViewTest', 'image_url': '',
        }, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN,
        ])

    def test_retrieve_product(self):
        p = Product.objects.create(title='RetrieveMe', price=Decimal('50.00'), category=self.cat)
        response = self.client.get(f'/products/{p.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'RetrieveMe')

    def test_delete_product(self):
        p = Product.objects.create(title='DeleteMe', price=Decimal('50.00'), category=self.cat)
        response = self.client.delete(f'/products/{p.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        p.refresh_from_db()
        self.assertTrue(p.is_deleted)

    def test_filter_by_category(self):
        cat2 = Category.objects.create(name='Other')
        Product.objects.create(title='InCat', price=Decimal('10.00'), category=self.cat)
        Product.objects.create(title='InOther', price=Decimal('20.00'), category=cat2)
        response = self.client.get('/products/?category=ViewTest')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_search_endpoint_fallback_to_db(self):
        Product.objects.create(title='Laptop Pro', price=Decimal('50000.00'), category=self.cat)
        with patch('products.views.search_products', return_value=[]):
            response = self.client.get('/products/search/?q=Laptop')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['source'], 'database')

    def test_search_endpoint_uses_es_when_available(self):
        es_results = [{'id': 1, 'title': 'Laptop ES', 'price': 50000.0, 'category': 'ViewTest'}]
        with patch('products.views.search_products', return_value=es_results):
            response = self.client.get('/products/search/?q=Laptop')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['source'], 'elasticsearch')
        self.assertEqual(len(response.data['results']), 1)


class TestProductCaching(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cat = Category.objects.create(name='CacheCat')
        from django.core.cache import cache
        cache.clear()

    def test_detail_is_cached_after_first_read(self):
        from django.core.cache import cache
        p = Product.objects.create(title='Cached', price=Decimal('10.00'), category=self.cat)
        # First read populates the cache
        self.client.get(f'/products/{p.id}/')
        self.assertIsNotNone(cache.get(f'products:detail:{p.id}'))

    def test_write_invalidates_cache(self):
        from django.core.cache import cache
        import jwt
        from django.conf import settings
        p = Product.objects.create(title='Cached', price=Decimal('10.00'), category=self.cat)
        self.client.get(f'/products/{p.id}/')
        self.assertIsNotNone(cache.get(f'products:detail:{p.id}'))
        # Authenticated delete should invalidate the cache
        token = jwt.encode(
            {'user_id': 1, 'email': 'a@b.com', 'role': 'admin', 'is_staff': True},
            settings.JWT_SECRET_KEY, algorithm='HS256',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.client.delete(f'/products/{p.id}/')
        self.assertIsNone(cache.get(f'products:detail:{p.id}'))


class TestCategoryViewSet(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_categories(self):
        Category.objects.create(name='Cat1')
        response = self.client.get('/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

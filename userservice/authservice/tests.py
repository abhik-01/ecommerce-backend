import pytest
from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from authservice.models import User, Role


class TestUserModel(TestCase):
    def setUp(self):
        self.role, _ = Role.objects.get_or_create(role='user')

    def test_create_user(self):
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role=self.role,
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_user_str(self):
        user = User.objects.create_user(email='str@example.com', password='pass')
        self.assertEqual(str(user), 'str@example.com')

    def test_email_is_unique(self):
        User.objects.create_user(email='unique@example.com', password='pass')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email='unique@example.com', password='pass2')


class TestRoleModel(TestCase):
    def test_role_creation(self):
        role = Role.objects.create(role='moderator')
        self.assertEqual(str(role), 'moderator')

    def test_default_roles_exist(self):
        self.assertTrue(Role.objects.filter(role='user').exists())
        self.assertTrue(Role.objects.filter(role='admin').exists())


class TestSignupView(TestCase):
    def setUp(self):
        self.client = APIClient()
        Role.objects.get_or_create(role='user')

    @patch('authservice.views.publish_user_registered')
    def test_signup_success(self, mock_publish):
        response = self.client.post('/auth/signup/', {
            'email': 'newuser@example.com',
            'password': 'strongpass123',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'SUCCESS')
        mock_publish.assert_called_once()
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_signup_missing_email(self):
        response = self.client.post('/auth/signup/', {'password': 'pass123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_missing_password(self):
        response = self.client.post('/auth/signup/', {'email': 'nopass@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('authservice.views.publish_user_registered')
    def test_signup_duplicate_email(self, mock_publish):
        self.client.post('/auth/signup/', {'email': 'dup@example.com', 'password': 'pass123'}, format='json')
        response = self.client.post('/auth/signup/', {'email': 'dup@example.com', 'password': 'pass456'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_invalid_role(self):
        response = self.client.post('/auth/signup/', {
            'email': 'role@example.com',
            'password': 'pass123',
            'role': 'nonexistent_role',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestValidateView(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_validate_unauthenticated(self):
        response = self.client.post('/auth/validate/')
        self.assertFalse(response.data['valid'])

    def test_validate_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalidtoken123')
        response = self.client.post('/auth/validate/')
        self.assertFalse(response.data['valid'])

    def test_validate_valid_jwt_returns_identity(self):
        import jwt
        from datetime import datetime, timedelta
        from django.conf import settings
        token = jwt.encode(
            {
                'user_id': 42,
                'email': 'jwtuser@example.com',
                'role': 'user',
                'exp': datetime.utcnow() + timedelta(hours=1),
                'iat': datetime.utcnow(),
            },
            settings.JWT_SECRET_KEY,
            algorithm='HS256',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post('/auth/validate/')
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['user_id'], 42)
        self.assertEqual(response.data['email'], 'jwtuser@example.com')
        self.assertEqual(response.data['role'], 'user')


class TestLogoutView(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_logout_without_token_returns_error(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer faketoken')
        response = self.client.post('/auth/logout/')
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ])

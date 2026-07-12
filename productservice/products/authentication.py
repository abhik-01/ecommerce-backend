import jwt
from os import getenv
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JWTUser(dict):
    """Decoded JWT claims that also satisfy DRF's IsAuthenticated check.

    Behaves like a dict (request.user['user_id'] / .get('user_id')) while
    exposing the attributes DRF permission classes expect on request.user.
    """

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_staff(self):
        return bool(self.get('is_staff'))

    @property
    def id(self):
        return self.get('user_id')


class JWTAuthentication(BaseAuthentication):
    """Validate the inter-service JWT issued by userservice.

    On success, request.user is a JWTUser (decoded claims) and request.auth
    is the raw token. Returns None for anonymous requests so permission_classes
    decide access.
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None  # anonymous — let permission_classes decide
        token = auth_header.split(' ', 1)[1]
        try:
            payload = jwt.decode(
                token,
                getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-prod'),
                algorithms=['HS256'],
            )
            return (JWTUser(payload), token)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')

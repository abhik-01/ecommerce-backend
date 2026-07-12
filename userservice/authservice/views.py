import json
import logging
from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from oauth2_provider.models import AccessToken
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from oauth2_provider.views import TokenView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    SignupSerializer, ProfileSerializer,
    ProfileUpdateSerializer, PasswordChangeSerializer,
)
from .kafka_producer import publish_user_registered

logger = logging.getLogger(__name__)


class AuthViewSet(viewsets.ViewSet):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def signup(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                publish_user_registered(user.id, user.email)
                return Response(
                    {'status': 'SUCCESS', 'message': 'User created'},
                    status=status.HTTP_201_CREATED,
                )
            except ValidationError as e:
                return Response(
                    {'status': 'FAILURE', 'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(
            {'status': 'FAILURE', 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def validate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return Response({'valid': False}, status=status.HTTP_401_UNAUTHORIZED)
        token_str = auth_header.split(' ', 1)[1]
        # Try JWT first (fast, no DB)
        try:
            payload = jwt.decode(token_str, settings.JWT_SECRET_KEY, algorithms=['HS256'])
            return Response({
                'valid': True,
                'user_id': payload['user_id'],
                'email': payload['email'],
                'role': payload.get('role', 'user'),
            })
        except jwt.PyJWTError:
            pass
        # Fallback: OAuth2 token DB lookup
        try:
            access_token = AccessToken.objects.select_related('user__role').get(token=token_str)
            if not access_token.is_valid():
                return Response({'valid': False}, status=status.HTTP_401_UNAUTHORIZED)
            user = access_token.user
            return Response({
                'valid': True,
                'user_id': user.id,
                'email': user.email,
                'role': user.role.role if user.role else 'user',
            })
        except AccessToken.DoesNotExist:
            return Response({'valid': False}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return Response(
                {'status': 'FAILURE', 'message': 'Token required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token = auth_header.split()[-1]
        try:
            access_token = AccessToken.objects.get(token=token)
            access_token.delete()
            return Response(
                {'status': 'SUCCESS', 'message': 'Logged out successfully'},
                status=status.HTTP_200_OK,
            )
        except AccessToken.DoesNotExist:
            return Response(
                {'status': 'FAILURE', 'message': 'Invalid or already logged out token'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=['get', 'patch'])
    def profile(self, request):
        user = request.user
        if request.method == 'GET':
            return Response(ProfileSerializer(user).data)
        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ProfileSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save(update_fields=['password'])
            return Response({'status': 'SUCCESS', 'message': 'Password updated'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenView(TokenView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        try:
            data = json.loads(response.content.decode())
        except Exception:
            data = {}

        if (
            response.status_code == status.HTTP_200_OK
            and data.get('access_token')
            and request.POST.get('grant_type') == 'password'
        ):
            user_model = get_user_model()
            username = request.POST.get('username')
            try:
                user = user_model.objects.get(email=username)
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])

                # Issue JWT for inter-service auth
                jwt_payload = {
                    'user_id': user.id,
                    'email': user.email,
                    'role': user.role.role if hasattr(user, 'role') and user.role else 'user',
                    'is_staff': user.is_staff,
                    'exp': datetime.utcnow() + timedelta(hours=1),
                    'iat': datetime.utcnow(),
                }
                data['jwt_token'] = jwt.encode(jwt_payload, settings.JWT_SECRET_KEY, algorithm='HS256')
                response.content = json.dumps(data).encode()
            except user_model.DoesNotExist:
                pass

        return response

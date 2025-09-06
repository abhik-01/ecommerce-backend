from django.core.exceptions import ValidationError
from oauth2_provider.models import AccessToken
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .serializers import SignupSerializer
from oauth2_provider.views import TokenView
from django.utils import timezone
from django.contrib.auth import get_user_model
import json


class AuthViewSet(viewsets.ViewSet):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def signup(self, request):
        serializer = SignupSerializer(data=request.data)

        if serializer.is_valid():
            try:
                serializer.save()

                return Response({'status': 'SUCCESS', 'message': 'User created'}, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({'status': 'FAILURE', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 'FAILURE', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def validate(self, request):
        if request.user and request.user.is_authenticated:
            return Response({'valid': True}, status=status.HTTP_200_OK)

        return Response({'valid': False}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if not auth_header:
            return Response({'status': 'FAILURE', 'message': 'Token required'}, status=status.HTTP_400_BAD_REQUEST)

        token = auth_header.split()[-1]

        try:
            access_token = AccessToken.objects.get(token=token)
            access_token.delete()

            return Response({'status': 'SUCCESS', 'message': 'Logged out successfully'}, status=status.HTTP_200_OK)

        except AccessToken.DoesNotExist:
            return Response({'status': 'FAILURE', 'message': 'Invalid or already logged out token'}, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenView(TokenView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        try:
            data = json.loads(response.content.decode())
        except Exception:
            data = {}

        if (
            response.status_code == status.HTTP_200_OK and
            data.get('access_token') and
            request.POST.get('grant_type') == 'password'
        ):
            user_model = get_user_model()
            username = request.POST.get('username')

            try:
                user = user_model.objects.get(email=username)
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
            except user_model.DoesNotExist:
                pass

        return response

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import NotificationLog
from .serializers import NotificationLogSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer

    def get_permissions(self):
        if self.action == 'health':
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def health(self, request):
        return Response({'status': 'ok', 'service': 'notificationservice'})

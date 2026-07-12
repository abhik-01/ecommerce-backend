from rest_framework import serializers
from .models import NotificationLog


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = ['id', 'event_type', 'recipient', 'subject', 'status', 'error_message', 'created_at']
        read_only_fields = fields

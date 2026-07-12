from django.db import models


class NotificationLog(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]

    event_type = models.CharField(max_length=100, db_index=True)
    recipient = models.EmailField(db_index=True)
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    error_message = models.TextField(blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_type} → {self.recipient} [{self.status}]'

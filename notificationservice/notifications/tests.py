import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from notifications.models import NotificationLog
from notifications.services import (
    EmailService, handle_user_registered, handle_order_created,
    handle_payment_completed, handle_payment_failed,
)


class TestNotificationLogModel(TestCase):
    def test_create_log(self):
        log = NotificationLog.objects.create(
            event_type='user.registered',
            recipient='test@example.com',
            subject='Welcome',
            status='sent',
            payload={'user_id': 1},
        )
        assert log.id is not None
        assert str(log) == 'user.registered → test@example.com [sent]'

    def test_default_status_is_sent(self):
        log = NotificationLog.objects.create(
            event_type='test.event',
            recipient='a@b.com',
            subject='Test',
            payload={},
        )
        assert log.status == 'sent'


class TestEmailService(TestCase):
    @patch('notifications.services.send_mail')
    def test_send_success(self, mock_send):
        log = EmailService.send(
            recipient='user@example.com',
            subject='Hello',
            body='World',
            event_type='test.event',
            payload={'key': 'val'},
        )
        mock_send.assert_called_once()
        assert log.status == 'sent'
        assert log.recipient == 'user@example.com'

    @patch('notifications.services.send_mail', side_effect=Exception('SMTP error'))
    def test_send_failure_logs_error(self, mock_send):
        log = EmailService.send(
            recipient='user@example.com',
            subject='Hello',
            body='World',
            event_type='test.event',
            payload={},
        )
        assert log.status == 'failed'
        assert 'SMTP error' in log.error_message


class TestEventHandlers(TestCase):
    @patch('notifications.services.EmailService.send')
    def test_handle_user_registered(self, mock_send):
        handle_user_registered({'email': 'new@user.com', 'user_id': 42})
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs['recipient'] == 'new@user.com'
        assert call_kwargs['event_type'] == 'user.registered'

    @patch('notifications.services.EmailService.send')
    def test_handle_user_registered_no_email(self, mock_send):
        handle_user_registered({'user_id': 99})
        mock_send.assert_not_called()

    @patch('notifications.services.EmailService.send')
    def test_handle_order_created(self, mock_send):
        handle_order_created({
            'order_id': 10, 'user_id': 1, 'total_amount': '500.00',
            'items': [{'product_id': 5, 'quantity': 2, 'price': '250.00'}],
            'email': 'buyer@example.com',
        })
        mock_send.assert_called_once()
        assert mock_send.call_args[1]['event_type'] == 'order.created'

    @patch('notifications.services.EmailService.send')
    def test_handle_payment_completed(self, mock_send):
        handle_payment_completed({
            'order_id': 10, 'amount': '500.00', 'currency': 'INR',
            'email': 'buyer@example.com',
        })
        mock_send.assert_called_once()
        assert 'Payment Received' in mock_send.call_args[1]['subject']

    @patch('notifications.services.EmailService.send')
    def test_handle_payment_failed(self, mock_send):
        handle_payment_failed({'order_id': 10, 'reason': 'Insufficient funds', 'email': 'buyer@example.com'})
        mock_send.assert_called_once()
        assert mock_send.call_args[1]['event_type'] == 'payment.failed'

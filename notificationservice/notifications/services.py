import logging
from django.core.mail import send_mail
from django.conf import settings
from .models import NotificationLog

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send(recipient: str, subject: str, body: str, event_type: str, payload: dict) -> NotificationLog:
        status = 'sent'
        error_message = ''
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            logger.info("Email sent to %s for event '%s'", recipient, event_type)
        except Exception as exc:
            status = 'failed'
            error_message = str(exc)
            logger.error("Email failed to %s for event '%s': %s", recipient, event_type, exc)

        return NotificationLog.objects.create(
            event_type=event_type,
            recipient=recipient,
            subject=subject,
            status=status,
            error_message=error_message,
            payload=payload,
        )


def handle_user_registered(payload: dict) -> None:
    email = payload.get('email', '')
    if not email:
        return
    subject = 'Welcome to Our Store!'
    body = (
        f"Hi,\n\n"
        f"Welcome to our ecommerce platform! Your account has been created successfully.\n\n"
        f"Email: {email}\n\n"
        f"Start shopping now!\n\nThank you."
    )
    EmailService.send(recipient=email, subject=subject, body=body,
                      event_type='user.registered', payload=payload)


def handle_order_created(payload: dict) -> None:
    user_id = payload.get('user_id')
    order_id = payload.get('order_id')
    total = payload.get('total_amount', '0')
    items = payload.get('items', [])
    recipient = payload.get('email', f'user_{user_id}@ecommerce.internal')
    items_text = '\n'.join(
        f"  - Product {i.get('product_id')}: qty {i.get('quantity')} @ {i.get('price')}"
        for i in items
    )
    subject = f'Order #{order_id} Confirmed'
    body = (
        f"Your order has been confirmed!\n\n"
        f"Order ID: {order_id}\n"
        f"Total: {total}\n\n"
        f"Items:\n{items_text}\n\n"
        f"We will notify you when your order ships."
    )
    EmailService.send(recipient=recipient, subject=subject, body=body,
                      event_type='order.created', payload=payload)


def handle_order_status_updated(payload: dict) -> None:
    order_id = payload.get('order_id')
    user_id = payload.get('user_id')
    new_status = payload.get('status', '')
    recipient = payload.get('email', f'user_{user_id}@ecommerce.internal')
    subject = f'Order #{order_id} Status Update'
    body = (
        f"Your order status has been updated.\n\n"
        f"Order ID: {order_id}\n"
        f"New Status: {new_status}\n\n"
        f"Thank you for shopping with us!"
    )
    EmailService.send(recipient=recipient, subject=subject, body=body,
                      event_type='order.status.updated', payload=payload)


def handle_payment_completed(payload: dict) -> None:
    order_id = payload.get('order_id')
    amount = payload.get('amount', '0')
    currency = payload.get('currency', 'INR')
    recipient = payload.get('email', f'order_{order_id}@ecommerce.internal')
    subject = f'Payment Received for Order #{order_id}'
    body = (
        f"We have received your payment.\n\n"
        f"Order ID: {order_id}\n"
        f"Amount: {amount} {currency}\n\n"
        f"Your order is being processed. Thank you!"
    )
    EmailService.send(recipient=recipient, subject=subject, body=body,
                      event_type='payment.completed', payload=payload)


def handle_payment_failed(payload: dict) -> None:
    order_id = payload.get('order_id')
    reason = payload.get('reason', 'Unknown error')
    recipient = payload.get('email', f'order_{order_id}@ecommerce.internal')
    subject = f'Payment Failed for Order #{order_id}'
    body = (
        f"Unfortunately, your payment could not be processed.\n\n"
        f"Order ID: {order_id}\n"
        f"Reason: {reason}\n\n"
        f"Please try again or contact support."
    )
    EmailService.send(recipient=recipient, subject=subject, body=body,
                      event_type='payment.failed', payload=payload)


EVENT_HANDLERS = {
    'user.registered': handle_user_registered,
    'order.created': handle_order_created,
    'order.status.updated': handle_order_status_updated,
    'payment.completed': handle_payment_completed,
    'payment.failed': handle_payment_failed,
}

from .models import Order, OrderItem, OrderTracking
from django.db import transaction
from .kafka_producer import publish_order_created, publish_order_status_updated


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(user_id, items, total_amount, payment_id=None):
        order = Order.objects.create(
            user_id=user_id,
            status='CONFIRMED',
            total_amount=total_amount,
            payment_id=payment_id,
            delivery_status='NOT_SHIPPED',
        )
        for item in items:
            OrderItem.objects.create(
                order=order,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price'],
            )
        publish_order_created(
            order_id=order.id,
            user_id=user_id,
            total_amount=str(total_amount),
            items=items,
        )
        return order

    @staticmethod
    def get_order_history(user_id):
        return Order.objects.filter(user_id=user_id).order_by('-created_at')

    @staticmethod
    def get_order_tracking(order_id):
        return OrderTracking.objects.filter(order_id=order_id).order_by('timestamp')

    @staticmethod
    def update_delivery_status(order_id, status, location=None):
        order = Order.objects.get(id=order_id)
        order.delivery_status = status
        order.save()
        tracking = OrderTracking.objects.create(
            order=order,
            status=status,
            location=location,
        )
        publish_order_status_updated(
            order_id=order.id,
            user_id=order.user_id,
            status=status,
        )
        return tracking

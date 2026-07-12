from rest_framework import serializers
from .models import Order, OrderItem, OrderTracking


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_id', 'quantity', 'price']


class OrderTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderTracking
        fields = ['id', 'status', 'timestamp', 'location']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    tracking = OrderTrackingSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user_id', 'status', 'total_amount', 'payment_id',
            'delivery_status', 'created_at', 'updated_at', 'items', 'tracking'
        ]


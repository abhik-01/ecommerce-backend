from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import OrderSerializer, OrderTrackingSerializer
from .services import OrderService
from .models import Order


def _resolve_user_id(request):
    """Return the authenticated user's ID from the JWT payload."""
    if isinstance(request.user, dict):
        return request.user.get('user_id')
    if request.user and request.user.is_authenticated:
        return request.user.id
    return request.data.get('user_id') or request.query_params.get('user_id')


class OrderViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user_id = _resolve_user_id(request)
        if not user_id:
            return Response({'error': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        orders = OrderService.get_order_history(user_id)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def create(self, request):
        user_id = _resolve_user_id(request)
        items = request.data.get('items', [])
        total_amount = request.data.get('total_amount')
        payment_id = request.data.get('payment_id')
        if not items or not total_amount:
            return Response({'error': 'Items and total_amount are required.'}, status=status.HTTP_400_BAD_REQUEST)
        order = OrderService.create_order(user_id, items, total_amount, payment_id)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='tracking')
    def tracking(self, request, pk=None):
        # Get tracking info for an order
        tracking = OrderService.get_order_tracking(pk)
        serializer = OrderTrackingSerializer(tracking, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='update_status', permission_classes=[permissions.IsAdminUser])
    def update_status(self, request, pk=None):
        # Update delivery status (admin only)
        status_val = request.data.get('status')
        location = request.data.get('location')
        if not status_val:
            return Response({'error': 'Status is required.'}, status=status.HTTP_400_BAD_REQUEST)
        tracking = OrderService.update_delivery_status(pk, status_val, location)
        serializer = OrderTrackingSerializer(tracking)
        return Response(serializer.data, status=status.HTTP_200_OK)

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import Cart
from .serializers import (
    CartSerializer, AddToCartInputSerializer, UpdateCartItemInputSerializer,
    RemoveCartItemInputSerializer, CheckoutCartInputSerializer
)
from .services import CartService
import mongoengine


def _user_id(request):
    """Extract user_id from the validated JWT payload (request.user is a dict)."""
    return str(request.user.get('user_id'))


class CartViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    cart_service = CartService()

    def retrieve(self, request, pk=None):
        try:
            cart = Cart.objects.get(cart_id=pk)
        except mongoengine.errors.DoesNotExist:
            return Response({'detail': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CartSerializer(cart.to_mongo().to_dict())
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        cart_data = self.cart_service.review_cart(_user_id(request))
        if cart_data is None:
            return Response({'detail': 'Cart not found for this user.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(cart_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def add(self, request):
        input_serializer = AddToCartInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        validated = input_serializer.validated_data
        cart = self.cart_service.add_to_cart(
            _user_id(request),
            validated['product_data'],
            validated['quantity']
        )
        output_serializer = CartSerializer(cart.to_mongo().to_dict())
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        input_serializer = UpdateCartItemInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        validated = input_serializer.validated_data
        cart = self.cart_service.update_cart_item(
            _user_id(request),
            validated['product_id'],
            validated['quantity']
        )
        output_serializer = CartSerializer(cart.to_mongo().to_dict())
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def remove(self, request):
        input_serializer = RemoveCartItemInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        validated = input_serializer.validated_data
        cart = self.cart_service.remove_from_cart(
            _user_id(request),
            validated['product_id']
        )
        output_serializer = CartSerializer(cart.to_mongo().to_dict())
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        input_serializer = CheckoutCartInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        validated = input_serializer.validated_data
        result = self.cart_service.checkout_cart(
            _user_id(request),
            validated['address'],
            validated['payment_method']
        )
        result['cart'] = CartSerializer(result['cart']).data if isinstance(result['cart'], dict) else result['cart']
        return Response(result, status=status.HTTP_200_OK)

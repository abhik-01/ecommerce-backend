from rest_framework import serializers


class CartItemSerializer(serializers.Serializer):
    product_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    price = serializers.FloatField()
    quantity = serializers.IntegerField(min_value=1)
    image_url = serializers.CharField(max_length=1024, required=False, allow_blank=True)
    total = serializers.FloatField(read_only=True)


class CartSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField(read_only=True)
    user_id = serializers.CharField(max_length=255)
    items = CartItemSerializer(many=True)


class AddToCartInputSerializer(serializers.Serializer):
    product_data = CartItemSerializer()
    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateCartItemInputSerializer(serializers.Serializer):
    product_id = serializers.CharField(max_length=255)
    quantity = serializers.IntegerField(min_value=1)


class RemoveCartItemInputSerializer(serializers.Serializer):
    product_id = serializers.CharField(max_length=255)


class CheckoutCartInputSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=1024)
    payment_method = serializers.CharField(max_length=255)

from rest_framework import serializers
from .models import Product, Category


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the Product model.
    Converts model instances to JSON and validates input data.
    """
    category = serializers.CharField(max_length=100)

    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'price', 'image_url', 'category']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['category'] = instance.category.name

        return representation


class CategoryIdSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(required=True, min_value=1)

    class Meta:
        fields = ['category_id']


class AddFeaturedSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True, min_value=1)
    category_id = serializers.IntegerField(required=True, min_value=1)

    class Meta:
        fields = ['product_id', 'category_id']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Category
from .serializers import CategorySerializer, ProductSerializer, CategoryIdSerializer, AddFeaturedSerializer
from .services import CategoryService


class CategoryViewSet(viewsets.ViewSet):
    """
    ViewSet for Category related operations.
    """
    def list(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def products(self, request, pk):
        """
        List all products in a category using CategoryService.
        """
        data = {'category_id': pk}
        serializer = CategoryIdSerializer(data=data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        category_id = serializer.validated_data['category_id']
        products = CategoryService.get_category_products(category_id)
        products_serializer = ProductSerializer(products, many=True)

        return Response(products_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get', 'post'])
    def featured(self, request):
        """
        Mark a product as featured in the category using CategoryService.
        """
        if request.method == 'GET':
            featured_products = CategoryService.get_featured_products()
            serializer = ProductSerializer(featured_products, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)

        if request.method == 'POST':
            serializer = AddFeaturedSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            product_id = serializer.validated_data['product_id']
            category_id = serializer.validated_data['category_id']

            CategoryService.add_featured_product(category_id, product_id)

            return Response({
                "success": f"Product {product_id} marked as featured in category {category_id}."},
                status=status.HTTP_200_OK
            )

        return Response(
            {"error": "Method not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

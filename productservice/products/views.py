from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter, NumberFilter
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import Product
from .serializers import ProductSerializer
from .services import ProductService
from .search import search_products

PRODUCT_CACHE_TTL = 300  # 5 minutes


def _invalidate_product_cache():
    """Drop all cached product list/detail entries after a write."""
    try:
        cache.delete_pattern('products:*')
    except Exception:
        # delete_pattern is django-redis specific; ignore on other backends
        cache.clear()


class ProductFilter(FilterSet):
    category = CharFilter(field_name='category__name', lookup_expr='iexact')
    min_price = NumberFilter(field_name='price', lookup_expr='gte')
    max_price = NumberFilter(field_name='price', lookup_expr='lte')

    class Meta:
        model = Product
        fields = ['category', 'min_price', 'max_price']


class ProductPagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 10


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category').filter(is_deleted=False)
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['title', 'description']
    filterset_class = ProductFilter
    ordering_fields = ['price', 'title']
    ordering = ['price']
    pagination_class = ProductPagination

    # Browsing is public; mutations require a valid JWT.
    WRITE_ACTIONS = {'create', 'update', 'partial_update', 'destroy'}

    def get_permissions(self):
        if self.action in self.WRITE_ACTIONS:
            return [IsAuthenticated()]
        return [AllowAny()]

    def list(self, request, *args, **kwargs):
        cache_key = f"products:list:{request.get_full_path()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            cache.set(cache_key, response.data, PRODUCT_CACHE_TTL)
        return response

    def retrieve(self, request, *args, **kwargs) -> Response:
        pk = kwargs.get('pk')
        cache_key = f"products:detail:{pk}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        product = ProductService.get_product_by_id(product_id=int(pk))
        data = ProductSerializer(product).data
        cache.set(cache_key, data, PRODUCT_CACHE_TTL)
        return Response(data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs) -> Response:
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            validated_data = serializer.validated_data
            product = ProductService.create_product(
                title=validated_data['title'],
                description=validated_data.get('description', ''),
                price=validated_data['price'],
                category_name=validated_data.get('category', ''),
                image_url=validated_data.get('image_url', ''),
            )
            _invalidate_product_cache()
            return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': f'Failed to create product: {e}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs) -> Response:
        pk = kwargs.get('pk')
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        product = ProductService.update_product(
            product_id=int(pk),
            title=validated_data['title'],
            description=validated_data.get('description', ''),
            price=validated_data['price'],
            category_name=validated_data.get('category', ''),
            image_url=validated_data.get('image_url', ''),
        )
        _invalidate_product_cache()
        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs) -> Response:
        pk = kwargs.get('pk')
        serializer = ProductSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = ProductService.partial_update_product(
            product_id=int(pk),
            **serializer.validated_data,
        )
        _invalidate_product_cache()
        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs) -> Response:
        pk = kwargs.get('pk')
        ProductService.delete_product(product_id=int(pk))
        _invalidate_product_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        q = request.query_params.get('q', '')
        category = request.query_params.get('category', '')
        min_price_raw = request.query_params.get('min_price')
        max_price_raw = request.query_params.get('max_price')

        min_price = float(min_price_raw) if min_price_raw else None
        max_price = float(max_price_raw) if max_price_raw else None

        results = search_products(
            query=q,
            category=category,
            min_price=min_price,
            max_price=max_price,
        )

        if results:
            return Response({'results': results, 'count': len(results), 'source': 'elasticsearch'})

        # Fallback to DB when ES is unavailable or returned nothing
        qs = Product.objects.select_related('category').filter(is_deleted=False)
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if category:
            qs = qs.filter(category__name__iexact=category)
        if min_price is not None:
            qs = qs.filter(price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)

        serializer = ProductSerializer(qs[:50], many=True)
        return Response({'results': serializer.data, 'count': qs.count(), 'source': 'database'})

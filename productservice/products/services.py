from django.db import transaction
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from .models import Product, Category


class ProductService:
    """
    Service layer for product-related business logic.
    """
    @staticmethod
    def create_product(title: str, description: str, price: float, category_name: str, image_url: str = "") -> Product:
        """
        Create a new product in the database.
        """
        with transaction.atomic():
            product = Product.create_with_category(
                title=title,
                description=description,
                price=price,
                image_url=image_url,
                category_name=category_name
            )

            return product

    # @staticmethod
    # def get_all_products() -> QuerySet:
    #     """
    #     Retrieve all products from the database.
    #     """
    #     return Product.objects.select_related('category').filter(is_deleted=False)  # solution to N+1 problem

    @staticmethod
    def get_product_by_id(product_id: int) -> Product:
        """
        Retrieve a product by its ID.
        """
        return get_object_or_404(
            Product,
            id=product_id,
            is_deleted=False
        )

    @staticmethod
    def update_product(product_id: int, title: str, description: str,
                       price: float, category_name: str, image_url: str) -> Product:
        """
        Fully update an existing product's fields.
        """
        with transaction.atomic():
            product = get_object_or_404(
                Product,
                id=product_id,
                is_deleted=False
            )

            if category_name:
                category = Category.get_or_create_by_name(category_name)
                product.category = category

            product.title = title
            product.description = description
            product.price = price
            product.image_url = image_url

            product.save()

            return product

    @staticmethod
    def partial_update_product(product_id: int, **kwargs) -> Product:
        """
        Partially update a product's fields.
        """
        with transaction.atomic():
            product = get_object_or_404(
                Product,
                id=product_id,
                is_deleted=False
            )

            if 'name' in kwargs:
                kwargs['title'] = kwargs.pop('name')

            if 'category' in kwargs:
                category_name = kwargs.pop('category')
                category = Category.get_or_create_by_name(category_name)
                product.category = category

            for attr, value in kwargs.items():
                if hasattr(product, attr):
                    setattr(product, attr, value)

            product.save()

            return product

    @staticmethod
    def delete_product(product_id: int) -> None:
        """
        Soft delete a product by marking it as deleted.
        """
        with transaction.atomic():
            product = get_object_or_404(Product, id=product_id, is_deleted=False)
            product.is_deleted = True
            product.save()


class CategoryService:
    """
    Service layer for category-related business logic.
    """
    @staticmethod
    def get_category_products(category_id: int) -> QuerySet:
        """
        Get all products in a category by id.
        """
        category = get_object_or_404(Category, pk=category_id, is_deleted=False)

        return category.all_products

    @staticmethod
    def add_featured_product(category_id: int, product_id: int) -> None:
        """
        Mark a product as featured in a category.
        """
        category = get_object_or_404(Category, pk=category_id, is_deleted=False)
        product = get_object_or_404(Product, pk=product_id, is_deleted=False)
        category.add_featured_product(product)

    @staticmethod
    def get_featured_products() -> QuerySet:
        """
        Get all featured products across all categories.
        """
        return Product.objects.filter(
            id__in=Category.objects.values_list('featured_products__id', flat=True),
            is_deleted=False
        ).distinct()

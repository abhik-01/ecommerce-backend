from django.db.models import (
    Model, CharField, TextField, DecimalField, URLField,
    DateTimeField, BooleanField, ForeignKey, CASCADE,
    ManyToManyField, QuerySet
)


class BaseModel(Model):
    """
    Abstract base model providing common fields for all models.
    """
    created_at = DateTimeField(auto_now_add=True)
    last_updated_at = DateTimeField(auto_now=True)
    is_deleted = BooleanField(default=False)

    class Meta:
        abstract = True


class Category(BaseModel):
    """
    Model representing a product category.
    """
    name = CharField(max_length=255, unique=True, db_column='category_name')
    description = TextField(blank=True)
    featured_products = ManyToManyField(
        'Product',
        blank=True,
        related_name='featured_in_categories'
    )

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'categories'

    def __str__(self) -> str:
        return self.name

    @property
    def all_products(self) -> QuerySet:
        """Get all products in this category"""
        return self.products.filter(is_deleted=False)

    def add_featured_product(self, product) -> None:
        """Add a product as featured, ensuring it's only featured in one category"""
        # Remove product from any other category's featured list
        for category in Category.objects.exclude(id=self.id):
            category.featured_products.remove(product)

        # Add to this category
        self.featured_products.add(product)

    @classmethod
    def get_or_create_by_name(cls, name: str, description: str = "") -> 'Category':
        """Get existing category or create new one."""
        category, created = cls.objects.get_or_create(
            name=name,
            is_deleted=False,
            defaults={'description': description}
        )
        return category


class Product(BaseModel):
    """
    Model representing a product.
    """
    title = CharField(max_length=255)
    description = TextField(blank=True)
    price = DecimalField(max_digits=10, decimal_places=2)
    image_url = URLField(blank=True)
    category = ForeignKey(
        Category,
        on_delete=CASCADE,
        related_name='products'
    )

    class Meta:
        db_table = 'products'

    def __str__(self) -> str:
        return self.title

    @classmethod
    def create_with_category(cls, title: str, description: str, price: float, image_url: str,
                             category_name: str) -> 'Product':
        """
        Create a new product with an associated category.
        """
        category = Category.get_or_create_by_name(category_name)

        return cls.objects.create(
            title=title,
            description=description,
            price=price,
            image_url=image_url,
            category=category
        )

from django.core.management.base import BaseCommand
from products.models import Product
from products.search import create_products_index, index_product


class Command(BaseCommand):
    help = 'Bulk index all active products into Elasticsearch'

    def handle(self, *args, **options):
        create_products_index()
        qs = Product.objects.select_related('category').filter(is_deleted=False)
        count = 0
        for product in qs.iterator():
            index_product(product)
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Indexed {count} products into Elasticsearch.'))

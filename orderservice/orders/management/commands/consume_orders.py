from django.core.management.base import BaseCommand
from orders.kafka_consumer import run_consumer


class Command(BaseCommand):
    help = 'Run the orderservice Kafka consumer (payment.completed / payment.failed)'

    def handle(self, *args, **options):
        self.stdout.write('Starting orderservice Kafka consumer...')
        run_consumer()

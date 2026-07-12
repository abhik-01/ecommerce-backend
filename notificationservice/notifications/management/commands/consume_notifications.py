from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run the Kafka consumer for notification events'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting notification Kafka consumer...'))
        try:
            from notifications.kafka_consumer import run_consumer
            run_consumer()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Consumer stopped.'))

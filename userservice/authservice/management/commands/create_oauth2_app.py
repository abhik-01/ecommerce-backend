import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Ensure the default OAuth2 Application exists'

    def handle(self, *args, **options):
        from oauth2_provider.models import Application
        app, created = Application.objects.get_or_create(
            name='ecommerce-default',
            defaults={
                'client_type': Application.CLIENT_CONFIDENTIAL,
                'authorization_grant_type': Application.GRANT_PASSWORD,
                'client_id': os.getenv('OAUTH2_CLIENT_ID', 'ecommerce-client'),
                'client_secret': os.getenv('OAUTH2_CLIENT_SECRET', 'ecommerce-secret'),
            },
        )
        self.stdout.write(
            f"OAuth2 app {'created' if created else 'already exists'}: {app.client_id}"
        )

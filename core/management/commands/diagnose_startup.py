from django.core.management.base import BaseCommand
from django.conf import settings
from django.apps import apps


class Command(BaseCommand):
    help = "Diagnose Django startup issues."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Attempting to diagnose Django startup..."))

        try:
            # Try to access settings
            self.stdout.write(f"DEBUG mode: {settings.DEBUG}")
            self.stdout.write(f"Installed apps count: {len(settings.INSTALLED_APPS)}")

            # Try to get an app config
            accounts_app = apps.get_app_config('accounts')
            self.stdout.write(f"Accounts app label: {accounts_app.label}")

            self.stdout.write(self.style.SUCCESS("Django core components appear to be accessible."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error during diagnosis: {e}"))
            import traceback
            traceback.print_exc()
            raise e

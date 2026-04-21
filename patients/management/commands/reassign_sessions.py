from django.core.management.base import BaseCommand
from screening.models import ScreeningSession
from accounts.models import User

class Command(BaseCommand):
    help = 'Reassigns all existing screening sessions to a specific Health Assistant'

    def add_arguments(self, parser):
        # We make it optional so we can list users if they don't provide a username
        parser.add_argument('username', nargs='?', type=str, help='The username of the Health Assistant')

    def handle(self, *args, **kwargs):
        username = kwargs.get('username')

        if not username:
            self.stdout.write(self.style.WARNING("You must provide your username to assign the sessions to yourself."))
            self.stdout.write("\n--- Available Health Assistants ---")
            for u in User.objects.filter(role='HEALTH_ASSISTANT'):
                self.stdout.write(f"Username: {u.username} | Name: {u.first_name} {u.last_name}")
            self.stdout.write("\nExample usage: python3 manage.py reassign_sessions john.doe")
            return

        try:
            # Change role filter if your users are sometimes SuperAdmins
            user = User.objects.get(username=username)
            count = ScreeningSession.objects.all().update(created_by=user)
            self.stdout.write(self.style.SUCCESS(f'Successfully reassigned {count} sessions to {user.username}!'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" not found.'))
            self.stdout.write("\n--- Available Health Assistants ---")
            for u in User.objects.filter(role='HEALTH_ASSISTANT'):
                self.stdout.write(f"Username: {u.username} | Name: {u.first_name} {u.last_name}")

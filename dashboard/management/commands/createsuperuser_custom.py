import os
import random
import string
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser with a secure random password'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Superuser username')
        parser.add_argument('--email', type=str, help='Superuser email')
        parser.add_argument('--password', type=str, help='Superuser password (if not provided, a random one will be generated)')

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')
        password = options.get('password')

        # If username or email not provided, prompt for them
        if not username:
            username = input('Enter username: ').strip()
        if not email:
            email = input('Enter email: ').strip()

        # If password not provided, generate a secure one
        if not password:
            # Generate a 16-character password with letters, digits, and special characters
            chars = string.ascii_letters + string.digits + '!@#$%^&*()_+=-'
            password = ''.join(random.choice(chars) for _ in range(16))

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User with username {username} already exists. Updating to superuser...'))
            user = User.objects.get(username=username)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Updated existing user {username} to superuser'))
        else:
            # Create new superuser
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Created superuser: {username}'))

        # Display the credentials
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Superuser created successfully!'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'Username: {username}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write('=' * 50)
        self.stdout.write(self.style.WARNING(
            'IMPORTANT: Save this password in a secure place. It will not be shown again.'
        ))
        self.stdout.write('=' * 50 + '\n')

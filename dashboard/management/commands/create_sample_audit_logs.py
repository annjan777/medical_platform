from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random

from dashboard.models import AuditLog

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample audit logs for testing'

    def handle(self, *args, **options):
        # Get or create a superuser for testing
        admin_user, created = User.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True
            }
        )
        
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Created admin user: admin@example.com/admin123'))

        # Sample audit log data
        sample_actions = [
            ('create', 'User', 'Created new user john.doe@example.com'),
            ('update', 'User', 'Updated user profile for jane.smith@example.com'),
            ('delete', 'Device', 'Deleted device Device-001'),
            ('access', 'Admin Dashboard', 'Accessed admin dashboard'),
            ('login', 'User', 'User login: admin@example.com'),
            ('logout', 'User', 'User logout: admin@example.com'),
            ('create', 'Questionnaire', 'Created new questionnaire: Medical Screening'),
            ('update', 'Questionnaire', 'Updated questionnaire: Patient Registration'),
            ('delete', 'Questionnaire', 'Deleted questionnaire: Old Screening Form'),
            ('access', 'Audit Logs', 'Accessed audit logs page'),
        ]

        # Clear existing audit logs
        AuditLog.objects.all().delete()
        
        # Create sample audit logs
        for i, (action, model, object_repr) in enumerate(sample_actions):
            # Create logs with different timestamps
            timestamp = timezone.now() - timedelta(days=random.randint(0, 30))
            
            audit_log = AuditLog.objects.create(
                user=admin_user,
                action=action,
                model=model,
                object_repr=object_repr,
                timestamp=timestamp,
                ip_address=f'192.168.1.{random.randint(1, 255)}'
            )
            
            self.stdout.write(f'Created audit log: {action} - {model} - {object_repr}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(sample_actions)} sample audit logs')
        )

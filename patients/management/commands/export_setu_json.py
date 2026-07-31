import os
import json
from django.core.management.base import BaseCommand
from patients.models import Patient

# Disable S3 connection and MQTT listeners to prevent networking blocks during CLI commands
os.environ['AWS_ACCESS_KEY_ID'] = ''
os.environ['AWS_SECRET_ACCESS_KEY'] = ''
os.environ['MQTT_ENABLED'] = 'False'

class Command(BaseCommand):
    help = 'Export all patient records in Setu MongoDB JSON format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='setu_migration_data.json',
            help='Output file path for the exported JSON'
        )

    def handle(self, *args, **options):
        # Import get_patient_setu_data here so Django has finished initializing
        from health_assistant.views import get_patient_setu_data
        
        output_file = options['output']
        self.stdout.write(f"Starting export of all patient records to {output_file}...")
        
        patients = Patient.objects.all().order_by('-created_at')
        total = patients.count()
        self.stdout.write(f"Found {total} patients to export.")
        
        data = []
        for i, patient in enumerate(patients):
            self.stdout.write(f"Processing patient {i+1}/{total}: {patient.patient_id} ({patient.full_name})...")
            try:
                record = get_patient_setu_data(patient)
                data.append(record)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error processing patient {patient.patient_id}: {str(e)}"))
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        self.stdout.write(self.style.SUCCESS(f"Successfully exported {len(data)} patient records to {output_file}"))

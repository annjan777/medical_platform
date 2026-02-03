from django.core.management.base import BaseCommand
from django.db import transaction
from patients.models import Patient, MedicalRecord, VitalSigns, PatientNote, Document
from screening.models import ScreeningSession, ScreeningResult
from questionnaires.models import Response, Answer

class Command(BaseCommand):
    help = 'Clear all patient data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompting',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING('WARNING: This will delete ALL patient data from the database!')
            )
            self.stdout.write('This includes:')
            self.stdout.write('- All patients')
            self.stdout.write('- All medical records')
            self.stdout.write('- All vital signs')
            self.stdout.write('- All patient notes')
            self.stdout.write('- All documents')
            self.stdout.write('- All screening sessions')
            self.stdout.write('- All screening results')
            self.stdout.write('- All questionnaire responses')
            self.stdout.write('- All questionnaire answers')
            
            confirm = input('\nType "DELETE ALL PATIENTS" to confirm: ')
            if confirm != 'DELETE ALL PATIENTS':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        try:
            with transaction.atomic():
                # Get counts before deletion
                patient_count = Patient.objects.count()
                response_count = Response.objects.count()
                session_count = ScreeningSession.objects.count()
                
                # Delete in order to respect foreign key constraints
                self.stdout.write('Deleting questionnaire answers...')
                Answer.objects.all().delete()
                
                self.stdout.write('Deleting questionnaire responses...')
                Response.objects.all().delete()
                
                self.stdout.write('Deleting screening results...')
                ScreeningResult.objects.all().delete()
                
                self.stdout.write('Deleting screening sessions...')
                ScreeningSession.objects.all().delete()
                
                self.stdout.write('Deleting patient documents...')
                Document.objects.all().delete()
                
                self.stdout.write('Deleting patient notes...')
                PatientNote.objects.all().delete()
                
                self.stdout.write('Deleting vital signs...')
                VitalSigns.objects.all().delete()
                
                self.stdout.write('Deleting medical records...')
                MedicalRecord.objects.all().delete()
                
                self.stdout.write('Deleting patients...')
                Patient.objects.all().delete()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully deleted:\n'
                        f'- {patient_count} patients\n'
                        f'- {response_count} questionnaire responses\n'
                        f'- {session_count} screening sessions'
                    )
                )
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error deleting patient data: {e}'))
            raise

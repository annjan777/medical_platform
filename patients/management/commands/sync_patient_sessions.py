from django.core.management.base import BaseCommand
from django.utils import timezone
from patients.models import Patient
from screening.models import ScreeningSession, ScreeningType
from accounts.models import User

class Command(BaseCommand):
    help = 'Creates missing screening sessions for existing patients'

    def handle(self, *args, **kwargs):
        # Get default screening type
        default_type = ScreeningType.objects.filter(is_active=True).first()
        if not default_type:
            default_type, _ = ScreeningType.objects.get_or_create(
                name="General Health Screening",
                defaults={"description": "Standard general health screening", "is_active": True}
            )

        ha = User.objects.filter(role='HEALTH_ASSISTANT').first()

        count = 0
        patients = Patient.objects.all()
        for patient in patients:
            # Check if session exists using patient ID
            if not ScreeningSession.objects.filter(patient=patient).exists():
                session = ScreeningSession.objects.create(
                    id=patient.patient_id,
                    patient=patient,
                    screening_type=default_type,
                    status=ScreeningSession.STATUS_IN_PROGRESS,
                    scheduled_date=timezone.now(),
                    consent_obtained=True,
                    consented_at=timezone.now()
                )
                
                # Assign created_by based on the patient's creator, fallback to a general HA
                if patient.created_by:
                    session.created_by = patient.created_by
                else:
                    session.created_by = ha
                    
                session.save()
                
                # Backdate the created_at to match the patient
                ScreeningSession.objects.filter(id=session.id).update(created_at=patient.created_at)
                count += 1
                
                self.stdout.write(f"Created session for patient: {patient.patient_id}")

        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} missing sessions!'))

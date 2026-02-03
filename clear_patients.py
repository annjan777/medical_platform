#!/usr/bin/env python3
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/Users/annjan/medical_platform')

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from patients.models import Patient, MedicalRecord, VitalSigns, PatientNote, Document
from screening.models import ScreeningSession, ScreeningResult
from questionnaires.models import Response, Answer

def clear_all_patients():
    """Clear all patient data from the database"""
    try:
        with transaction.atomic():
            # Get counts before deletion
            patient_count = Patient.objects.count()
            response_count = Response.objects.count()
            session_count = ScreeningSession.objects.count()
            
            print(f"Found {patient_count} patients, {response_count} responses, {session_count} screening sessions")
            
            # Delete in order to respect foreign key constraints
            print("Deleting questionnaire answers...")
            Answer.objects.all().delete()
            
            print("Deleting questionnaire responses...")
            Response.objects.all().delete()
            
            print("Deleting screening results...")
            ScreeningResult.objects.all().delete()
            
            print("Deleting screening sessions...")
            ScreeningSession.objects.all().delete()
            
            print("Deleting patient documents...")
            Document.objects.all().delete()
            
            print("Deleting patient notes...")
            PatientNote.objects.all().delete()
            
            print("Deleting vital signs...")
            VitalSigns.objects.all().delete()
            
            print("Deleting medical records...")
            MedicalRecord.objects.all().delete()
            
            print("Deleting patients...")
            Patient.objects.all().delete()
            
            print(f"\n✅ Successfully deleted:")
            print(f"   - {patient_count} patients")
            print(f"   - {response_count} questionnaire responses")
            print(f"   - {session_count} screening sessions")
            
    except Exception as e:
        print(f"❌ Error deleting patient data: {e}")
        raise

if __name__ == "__main__":
    clear_all_patients()

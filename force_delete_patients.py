#!/usr/bin/env python3
import os
import sys

# Add the project directory to the Python path
sys.path.append('/Users/annjan/medical_platform')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection
from patients.models import Patient, MedicalRecord, VitalSigns, PatientNote, Document
from screening.models import ScreeningSession, ScreeningResult
from questionnaires.models import Response, Answer

def force_delete_patients():
    """Force delete all patients and related data"""
    try:
        # Check current state
        patient_count = Patient.objects.count()
        print(f"Current patient count: {patient_count}")
        
        if patient_count > 0:
            print("Listing patients:")
            for patient in Patient.objects.all():
                print(f"  ID: {patient.id}, Name: {patient.get_full_name()}")
        
        # Delete all related data first
        print("Deleting related data...")
        Answer.objects.all().delete()
        Response.objects.all().delete()
        ScreeningResult.objects.all().delete()
        ScreeningSession.objects.all().delete()
        Document.objects.all().delete()
        PatientNote.objects.all().delete()
        VitalSigns.objects.all().delete()
        MedicalRecord.objects.all().delete()
        
        # Delete patients
        print("Deleting patients...")
        Patient.objects.all().delete()
        
        # Verify deletion
        remaining = Patient.objects.count()
        print(f"Remaining patients: {remaining}")
        
        if remaining == 0:
            print("✅ All patients deleted successfully!")
        else:
            print("⚠️  Some patients remain, trying direct SQL...")
            cursor = connection.cursor()
            cursor.execute("DELETE FROM patients_patient")
            cursor.execute("DELETE FROM patients_medicalrecord")
            cursor.execute("DELETE FROM patients_vitalsigns")
            cursor.execute("DELETE FROM patients_patientnote")
            cursor.execute("DELETE FROM patients_document")
            print("✅ Direct SQL deletion completed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        # Try direct SQL as last resort
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM patients_patient")
            print("✅ Direct SQL deletion completed")
        except Exception as e2:
            print(f"❌ SQL deletion also failed: {e2}")

if __name__ == "__main__":
    force_delete_patients()

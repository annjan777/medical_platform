from django.db import migrations
import re

def repad_patient_ids_to_6_digits(apps, schema_editor):
    """
    Updates all existing patient IDs from MDCP0001 (4 digits) to MDCP000001 (6 digits)
    to ensure consistent sorting and scaling support for up to 999,999 records in RDS.
    """
    Patient = apps.get_model('patients', 'Patient')
    print("Repadding existing patient IDs to 6 digits for RDS consistency...")
    
    updated_count = 0
    for patient in Patient.objects.all():
        if patient.patient_id and patient.patient_id.startswith('MDCP'):
            match = re.search(r'(\d+)', patient.patient_id)
            if match:
                num_part = int(match.group(1))
                new_id = f"MDCP{num_part:06d}"
                
                if patient.patient_id != new_id:
                    patient.patient_id = new_id
                    patient.save()
                    updated_count += 1
    
    if updated_count > 0:
        print(f"Successfully migrated {updated_count} records on RDS/AWS.")

class Migration(migrations.Migration):
    dependencies = [
        ('patients', '0011_alter_patient_phone_number'),
    ]

    operations = [
        migrations.RunPython(repad_patient_ids_to_6_digits),
    ]

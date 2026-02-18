# Generated migration for making phone_number mandatory and unique

from django.db import migrations, models
import re


class Migration(migrations.Migration):

    def __init__(self, app_label, model_name):
        super().__init__(app_label, model_name)

    def generate_sql_for_table(self, model):
        # This is a simplified migration - in production, use Django migrations
        return f"""
        -- Update patients table to make phone_number mandatory and unique
        -- Note: This is a simplified migration for demonstration
        -- In production, create proper Django migrations with:
        -- python manage.py makemigrations patients
        -- python manage.py migrate
        
        UPDATE patients 
        SET phone_number = CASE 
            WHEN phone_number IS NULL OR phone_number = '' THEN CONCAT('TEMP_', CAST(id AS TEXT))
            ELSE phone_number 
        END,
        phone_number = phone_number || CONCAT('TEMP_', CAST(id AS TEXT));
        """

    def apply(self, database):
        # For demonstration only - use Django migrations in production
        pass

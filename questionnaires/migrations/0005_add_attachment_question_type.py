# Generated migration for adding attachment question type

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questionnaires', '0004_auto_20260201_2250'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='question_type',
            field=models.CharField(
                choices=[
                    ('yes_no', 'Yes/No'),
                    ('true_false', 'True/False'),
                    ('multiple_choice', 'Multiple Choice'),
                    ('short_answer', 'Short Answer'),
                    ('attachment', 'Attachment'),
                ],
                max_length=20
            ),
        ),
    ]

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from questionnaires.models import Questionnaire, Question, QuestionOption

User = get_user_model()

class Command(BaseCommand):
    help = 'Create medical screening questionnaire with oral cancer screening questions'

    def handle(self, *args, **options):
        # Get or create a superuser for the questionnaire
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR('No superuser found. Please create a superuser first.'))
            return

        # Create the medical screening questionnaire
        questionnaire, created = Questionnaire.objects.get_or_create(
            title='Medical Screening Questionnaire',
            defaults={
                'description': 'Comprehensive medical screening questionnaire including oral cancer risk factors',
                'version': '1.0',
                'status': 'active',
                'questionnaire_type': 'screening',
                'is_active': True,
                'created_by': admin_user,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created medical screening questionnaire'))
        else:
            self.stdout.write(self.style.WARNING('Questionnaire already exists, updating questions...'))
            # Delete existing questions to start fresh
            questionnaire.questions.all().delete()

        # Define the questions and options
        questions_data = [
            {
                'text': 'Alcohol intake?',
                'question_type': 'radio',
                'is_required': True,
                'display_order': 1,
                'options': [
                    {'text': 'Yes', 'value': 'yes'},
                    {'text': 'No', 'value': 'no'},
                ]
            },
            {
                'text': 'Tobacco products (Cigarette / bidi / khaini / hookah)?',
                'question_type': 'radio',
                'is_required': True,
                'display_order': 2,
                'options': [
                    {'text': 'Yes', 'value': 'yes'},
                    {'text': 'No', 'value': 'no'},
                ]
            },
            {
                'text': 'Gutka (Areca Nut)?',
                'question_type': 'radio',
                'is_required': True,
                'display_order': 3,
                'options': [
                    {'text': 'Yes', 'value': 'yes'},
                    {'text': 'No', 'value': 'no'},
                ]
            },
            {
                'text': 'Paan with slaked lime, zarda and betel nut?',
                'question_type': 'radio',
                'is_required': True,
                'display_order': 4,
                'options': [
                    {'text': 'Yes', 'value': 'yes'},
                    {'text': 'No', 'value': 'no'},
                ]
            },
            {
                'text': 'Precipitation effect in the mouth due to tobacco or betel leaf?',
                'question_type': 'radio',
                'is_required': True,
                'display_order': 5,
                'options': [
                    {'text': 'Yes', 'value': 'yes'},
                    {'text': 'No', 'value': 'no'},
                ]
            },
            {
                'text': 'Have you ever been tested for HIV?',
                'question_type': 'radio',
                'is_required': True,
                'display_order': 6,
                'options': [
                    {'text': 'Yes', 'value': 'yes'},
                    {'text': 'No', 'value': 'no'},
                ]
            },
            {
                'text': 'Have you ever been tested for HPV?',
                'question_type': 'radio',
                'is_required': True,
                'display_order': 7,
                'options': [
                    {'text': 'Yes', 'value': 'yes'},
                    {'text': 'No', 'value': 'no'},
                ]
            },
            {
                'text': 'Family history of Head, Neck, Throat or oral cancer in blood relatives',
                'question_type': 'radio',
                'is_required': True,
                'display_order': 8,
                'options': [
                    {'text': 'Yes', 'value': 'yes'},
                    {'text': 'No', 'value': 'no'},
                ]
            },
        ]

        # Create questions and options
        for q_data in questions_data:
            question = Question.objects.create(
                questionnaire=questionnaire,
                text=q_data['text'],
                question_type=q_data['question_type'],
                is_required=q_data['is_required'],
                display_order=q_data['display_order'],
            )

            # Create options for this question
            for opt_data in q_data['options']:
                QuestionOption.objects.create(
                    question=question,
                    text=opt_data['text'],
                    value=opt_data['value'],
                    display_order=list(q_data['options']).index(opt_data),
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created medical screening questionnaire with {len(questions_data)} questions'
            )
        )

from django.core.management.base import BaseCommand
from django.db import transaction
from questionnaires.models import Questionnaire, Question, QuestionOption, Response, Answer
import sys

class Command(BaseCommand):
    help = 'Clean up old questionnaire data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without interactive prompt',
        )
        parser.add_argument(
            '--keep-recent',
            type=int,
            default=0,
            help='Keep questionnaires created in the last N days (default: 0, delete all)',
        )

    def handle(self, *args, **options):
        from django.utils import timezone
        from datetime import timedelta
        
        confirm = options['confirm']
        keep_recent_days = options['keep_recent']
        
        # Calculate cutoff date
        if keep_recent_days > 0:
            cutoff_date = timezone.now() - timedelta(days=keep_recent_days)
            questionnaires = Questionnaire.objects.filter(created_at__lt=cutoff_date)
            self.stdout.write(
                self.style.WARNING(
                    f'Will delete questionnaires created before {cutoff_date.strftime("%Y-%m-%d %H:%M")}'
                )
            )
        else:
            questionnaires = Questionnaire.objects.all()
            self.stdout.write(
                self.style.WARNING('Will delete ALL questionnaire data!')
            )
        
        # Count what will be deleted
        questionnaire_count = questionnaires.count()
        question_count = Question.objects.filter(questionnaire__in=questionnaires).count()
        option_count = QuestionOption.objects.filter(question__questionnaire__in=questionnaires).count()
        response_count = Response.objects.filter(questionnaire__in=questionnaires).count()
        answer_count = Answer.objects.filter(response__questionnaire__in=questionnaires).count()
        
        if questionnaire_count == 0:
            self.stdout.write(self.style.SUCCESS('No questionnaires to delete.'))
            return
        
        # Show what will be deleted
        self.stdout.write('\nData to be deleted:')
        self.stdout.write(f'  Questionnaires: {questionnaire_count}')
        self.stdout.write(f'  Questions: {question_count}')
        self.stdout.write(f'  Question Options: {option_count}')
        self.stdout.write(f'  Responses: {response_count}')
        self.stdout.write(f'  Answers: {answer_count}')
        
        # Confirmation
        if not confirm:
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.ERROR('WARNING: This will permanently delete all questionnaire data!'))
            self.stdout.write('Type "DELETE" to confirm:')
            response = input('> ')
            
            if response != 'DELETE':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return
        
        try:
            with transaction.atomic():
                # Delete in correct order to respect foreign key constraints
                self.stdout.write('\nDeleting data...')
                
                # Delete answers first
                Answer.objects.filter(response__questionnaire__in=questionnaires).delete()
                self.stdout.write('  ✓ Answers deleted')
                
                # Delete responses
                Response.objects.filter(questionnaire__in=questionnaires).delete()
                self.stdout.write('  ✓ Responses deleted')
                
                # Delete question options
                QuestionOption.objects.filter(question__questionnaire__in=questionnaires).delete()
                self.stdout.write('  ✓ Question options deleted')
                
                # Delete questions
                Question.objects.filter(questionnaire__in=questionnaires).delete()
                self.stdout.write('  ✓ Questions deleted')
                
                # Finally delete questionnaires
                questionnaires.delete()
                self.stdout.write('  ✓ Questionnaires deleted')
                
                self.stdout.write('\n' + '='*50)
                self.stdout.write(self.style.SUCCESS('✅ All questionnaire data has been successfully deleted!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during deletion: {e}'))
            sys.exit(1)

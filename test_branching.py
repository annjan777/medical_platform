import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_assistant.settings')
django.setup()

from questionnaires.models import Questionnaire, Question

q = Questionnaire.objects.create(title="Branching Test Auto")
q1 = Question.objects.create(questionnaire=q, question_text="Do you smoke?", question_type="yes_no", order=1)
q1_1 = Question.objects.create(questionnaire=q, question_text="How many packs a day?", question_type="short_answer", order=2, parent=q1, trigger_answer="yes")
q1_2 = Question.objects.create(questionnaire=q, question_text="Have you ever smoked?", question_type="yes_no", order=3, parent=q1, trigger_answer="no")
q2 = Question.objects.create(questionnaire=q, question_text="Do you drink?", question_type="yes_no", order=4)

print("Q1:", q1.get_display_number())
print("Q1 YES Followup:", q1_1.get_display_number())
print("Q1 NO Followup:", q1_2.get_display_number())
print("Q2:", q2.get_display_number())


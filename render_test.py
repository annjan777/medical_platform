import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_assistant.settings')
django.setup()

from questionnaires.models import Questionnaire
from django.template.loader import render_to_string
from questionnaires.forms import ResponseForm

q = Questionnaire.objects.get(title="Branchingtest")
questions = q.questions.all().order_by('order')
form = ResponseForm(q)

html = render_to_string('questionnaires/simple_questionnaire_display.html', {
    'questionnaire': q,
    'questions': questions,
    'form': form,
})

for line in html.split('\n'):
    if 'question-container' in line or 'data-parent-id' in line or 'style="display: none;"' in line:
        print(line.strip())

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_assistant.settings')
django.setup()

from questionnaires.models import Questionnaire
from questionnaires.forms import ResponseForm

q = Questionnaire.objects.get(title="Branchingtest")

# Simulate a submit where "Do You Play Guitar (yes/no)" is NO, 
# "Do you play Drums (yes/no)" is YES, 
# "Which drums do you have" is NOT submitted (empty).

# IDs: 67 (Guitar), 68 (Owe), 69 (Drums), 70 (Which Drums)
data = {
    "questionnaire_id": q.id,
    "question_67": "no",
    "question_68": "",      # Required but hidden! Should NOT Trigger Error
    "question_69": "yes",     
    "question_70": ""       # Required and VISIBLE! Should Trigger Error
}

form = ResponseForm(questionnaire=q, data=data)
form.is_valid()
print("Errors for Guitar=NO, Drums=YES, DrumsType=EMPTY:")
for field, errors in form.errors.items():
    print(f"  {field}: {errors}")


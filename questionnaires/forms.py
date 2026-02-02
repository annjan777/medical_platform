from django import forms
from django.forms import inlineformset_factory, formset_factory
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import (
    Questionnaire, Question, QuestionOption, Response, Answer
)

class QuestionnaireForm(forms.ModelForm):
    class Meta:
        model = Questionnaire
        fields = [
            'title', 'description', 'version', 'status',
            'questionnaire_type', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'is_active':
                field.widget.attrs.update({'class': 'form-check-input'})
            elif field_name in ['status', 'questionnaire_type']:
                field.widget.attrs.update({'class': 'form-select'})
            elif field_name == 'description':
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'question_text', 'question_type', 'is_required'
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'is_required':
                field.widget.attrs.update({'class': 'form-check-input'})
            elif field_name == 'question_type':
                field.widget.attrs.update({'class': 'form-select'})
            elif field_name == 'order':
                field.widget.attrs.update({'class': 'form-control', 'min': 0})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Special handling for boolean field
        self.fields['is_required'].widget.attrs.update({'class': 'form-check-input'})


class QuestionOptionForm(forms.ModelForm):
    class Meta:
        model = QuestionOption
        fields = ['text', 'option_image', 'order']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'option_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default order if not provided
        if not self.instance.pk and not self.initial.get('order'):
            question = self.initial.get('question')
            if question:
                last_option = question.options.order_by('-order').first()
                self.initial['order'] = (last_option.order + 1) if last_option else 0


# Formset for question options
QuestionOptionFormSet = inlineformset_factory(
    Question, QuestionOption, 
    form=QuestionOptionForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False
)


class ResponseForm(forms.ModelForm):
    class Meta:
        model = Response
        fields = ['respondent', 'patient', 'session', 'is_complete', 'ip_address', 'user_agent']
        widgets = {
            'respondent': forms.HiddenInput(),
            'patient': forms.HiddenInput(),
            'session': forms.HiddenInput(),
            'ip_address': forms.HiddenInput(),
            'user_agent': forms.HiddenInput(),
            'is_complete': forms.HiddenInput(),
        }
    
    def __init__(self, questionnaire, *args, **kwargs):
        self.questionnaire = questionnaire
        # Question model does not currently have an is_active flag; treat all as active.
        self.questions = questionnaire.questions.all().order_by('order')
        super().__init__(*args, **kwargs)
        
        # Set initial values for hidden fields
        request = kwargs.get('request')
        if request:
            self.fields['ip_address'].initial = request.META.get('REMOTE_ADDR')
            self.fields['user_agent'].initial = request.META.get('HTTP_USER_AGENT', '')[:500]  # Truncate if too long
        
        # Add fields for each question
        for question in self.questions:
            field_name = f'question_{question.id}'
            field = self.get_question_field(question)
            self.fields[field_name] = field
            
            # Set initial value if editing an existing response
            if self.instance and self.instance.pk:
                try:
                    answer = self.instance.answers.get(question=question)
                    if question.question_type in [Question.TYPE_CHECKBOX, Question.TYPE_RADIO, Question.TYPE_SELECT]:
                        self.initial[field_name] = answer.get_value()
                    else:
                        self.initial[field_name] = answer.get_value()
                except Answer.DoesNotExist:
                    pass
    
    def get_question_field(self, question):
        """Create a form field for a question based on its type."""
        field_name = f'question_{question.id}'
        field_kwargs = {
            'label': question.question_text,
            'required': question.is_required,
            'help_text': getattr(question, 'help_text', ''),
        }
        
        # Add question type specific attributes for simplified types
        if question.question_type in [question.TYPE_YES_NO, question.TYPE_TRUE_FALSE]:
            # For Yes/No and True/False, use ChoiceField with RadioSelect
            field_class = forms.ChoiceField
            if question.question_type == question.TYPE_YES_NO:
                choices = [('yes', 'Yes'), ('no', 'No')]
            else:  # True/False
                choices = [('true', 'True'), ('false', 'False')]
            field_kwargs['choices'] = choices
            field_kwargs['widget'] = forms.RadioSelect()
        elif question.question_type == question.TYPE_SHORT_ANSWER:
            # For short answer, use CharField with Textarea
            field_class = forms.CharField
            field_kwargs['widget'] = forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
        elif question.question_type == question.TYPE_MULTIPLE_CHOICE:
            # For multiple choice, use ChoiceField with RadioSelect
            field_class = forms.ChoiceField
            choices = [(opt.id, opt.text) for opt in question.options.all()]
            field_kwargs['choices'] = choices
            field_kwargs['widget'] = forms.RadioSelect()
        else:
            # Fallback for any other types
            field_class = forms.CharField
            field_kwargs['widget'] = forms.TextInput(attrs={'class': 'form-control'})
        
        field = field_class(**field_kwargs)
        self.fields[field_name] = field
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate required fields
        for question in self.questions:
            field_name = f'question_{question.id}'
            if question.is_required and not cleaned_data.get(field_name):
                self.add_error(field_name, 'This field is required.')
        
        return cleaned_data
    
    def save(self, commit=True):
        response = super().save(commit=False)
        response.questionnaire = self.questionnaire
        
        if commit:
            response.save()
            self.save_answers(response)
        
        return response
    
    def save_answers(self, response):
        """Save all answers for the response."""
        for question in self.questions:
            field_name = f'question_{question.id}'
            if field_name in self.cleaned_data:
                value = self.cleaned_data[field_name]
                
                # Get or create the answer
                answer, created = Answer.objects.get_or_create(
                    response=response,
                    question=question,
                    defaults={'text_answer': ''}
                )
                
                # Update the answer based on question type
                answer.option_answer.clear()
                answer.text_answer = ''
                answer.number_answer = None
                answer.date_answer = None

                if question.question_type in [Question.TYPE_RADIO, Question.TYPE_SELECT]:
                    # value is QuestionOption.value
                    if value:
                        opt = question.options.filter(value=value).first()
                        if opt:
                            answer.option_answer.add(opt)
                elif question.question_type == Question.TYPE_CHECKBOX:
                    values = value if isinstance(value, list) else ([value] if value else [])
                    if values:
                        opts = list(question.options.filter(value__in=values))
                        if opts:
                            answer.option_answer.add(*opts)
                elif question.question_type == Question.TYPE_NUMBER:
                    answer.number_answer = value if value is not None else None
                elif question.question_type == Question.TYPE_DATE:
                    answer.date_answer = value if value is not None else None
                elif question.question_type == Question.TYPE_FILE:
                    # File handling is managed by Django's ModelForm save via file_answer,
                    # but keep a fallback string if needed.
                    answer.text_answer = ''
                else:
                    answer.text_answer = str(value) if value is not None else ''
                
                answer.save()

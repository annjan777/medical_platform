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
            'text', 'help_text', 'question_type', 'is_required',
            'display_order', 'depends_on_question', 'depends_on_value',
            'allowed_file_types', 'max_file_size', 'min_value', 'max_value',
            'min_label', 'max_label'
        ]
        widgets = {
            'text': forms.Textarea(attrs={'rows': 2}),
            'help_text': forms.Textarea(attrs={'rows': 2}),
            'depends_on_value': forms.TextInput(attrs={'placeholder': 'Value that enables this question'}),
            'allowed_file_types': forms.TextInput(attrs={'placeholder': 'e.g., .pdf,.doc,.jpg'}),
            'min_label': forms.TextInput(attrs={'placeholder': 'e.g., Not at all likely'}),
            'max_label': forms.TextInput(attrs={'placeholder': 'e.g., Extremely likely'}),
        }
    
    def __init__(self, *args, **kwargs):
        questionnaire_id = kwargs.pop('questionnaire_id', None)
        super().__init__(*args, **kwargs)
        
        # Set the questionnaire for the question if provided
        if questionnaire_id:
            self.fields['depends_on_question'].queryset = Question.objects.filter(
                questionnaire_id=questionnaire_id
            )
        
        # Add CSS classes to form fields
        for field_name, field in self.fields.items():
            # Set appropriate CSS classes based on field type
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif field_name in ['min_value', 'max_value', 'max_file_size', 'display_order']:
                field.widget.attrs.update({'class': 'form-control', 'step': 'any'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
            
            # Add placeholder for text inputs if not already set
            if isinstance(field.widget, forms.TextInput) and 'placeholder' not in field.widget.attrs:
                field.widget.attrs['placeholder'] = field.label
        
        # Special handling for boolean field
        self.fields['is_required'].widget.attrs.update({'class': 'form-check-input'})
    
    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get('question_type')
        
        # Validate that depends_on_question is within the same questionnaire
        depends_on_question = cleaned_data.get('depends_on_question')
        questionnaire_id = getattr(self.instance, 'questionnaire_id', None)
        
        if depends_on_question and questionnaire_id and depends_on_question.questionnaire_id != questionnaire_id:
            raise ValidationError({
                'depends_on_question': 'Dependency must be a question from the same questionnaire.'
            })
        
        # Validate min/max values for numeric questions
        if question_type == Question.TYPE_NUMBER:
            min_val = cleaned_data.get('min_value')
            max_val = cleaned_data.get('max_value')
            
            if min_val is not None and max_val is not None and min_val > max_val:
                raise ValidationError({
                    'min_value': 'Minimum value cannot be greater than maximum value.'
                })
        
        # Validate file upload settings
        if question_type == Question.TYPE_FILE:
            allowed_types = cleaned_data.get('allowed_file_types', '')
            max_size = cleaned_data.get('max_file_size')
            
            if not allowed_types:
                self.add_error('allowed_file_types', 'Please specify allowed file types (e.g., .pdf,.jpg,.doc)')
            
            if max_size is not None and max_size <= 0:
                self.add_error('max_file_size', 'Maximum file size must be greater than 0')
        
        # Validate rating scale labels
        if question_type == Question.TYPE_RATING:
            min_label = cleaned_data.get('min_label')
            max_label = cleaned_data.get('max_label')
            
            if not min_label or not max_label:
                if not min_label:
                    self.add_error('min_label', 'Required for rating scale questions')
                if not max_label:
                    self.add_error('max_label', 'Required for rating scale questions')
        
        return cleaned_data


class QuestionOptionForm(forms.ModelForm):
    class Meta:
        model = QuestionOption
        fields = ['text', 'value', 'display_order', 'option_image', 'is_image_primary']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.TextInput(attrs={'class': 'form-control'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'option_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_image_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default display order if not provided
        if not self.instance.pk and not self.initial.get('display_order'):
            question = self.initial.get('question')
            if question:
                last_option = question.options.order_by('-display_order').first()
                self.initial['display_order'] = (last_option.display_order + 1) if last_option else 0,


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
        self.questions = questionnaire.questions.all().order_by('display_order')
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
            'label': question.text,
            'required': question.is_required,
            'help_text': question.help_text,
        }
        
        # Add question type specific attributes
        if question.question_type in [Question.TYPE_TEXT, Question.TYPE_EMAIL, Question.TYPE_TEXTAREA, Question.TYPE_NUMBER, Question.TYPE_DATE, Question.TYPE_FILE]:
            field_class = {
                Question.TYPE_TEXT: forms.CharField,
                Question.TYPE_EMAIL: forms.EmailField,
                Question.TYPE_TEXTAREA: forms.CharField,
                Question.TYPE_NUMBER: forms.FloatField,
                Question.TYPE_DATE: forms.DateField,
                Question.TYPE_FILE: forms.FileField,
            }[question.question_type]
            
            # Set widget based on question type
            if question.question_type == Question.TYPE_TEXTAREA:
                field_kwargs['widget'] = forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
            elif question.question_type == Question.TYPE_DATE:
                field_kwargs['widget'] = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
            elif question.question_type == Question.TYPE_FILE:
                field_kwargs['widget'] = forms.FileInput(attrs={'class': 'form-control'})
                if question.allowed_file_types:
                    field_kwargs['help_text'] = (field_kwargs.get('help_text', '') + 
                                               f" Allowed file types: {question.allowed_file_types}").strip()
            else:
                field_kwargs['widget'] = forms.TextInput(attrs={'class': 'form-control'})
            
            # Add validation for number fields
            if question.question_type == Question.TYPE_NUMBER:
                if question.min_value is not None:
                    field_kwargs['min_value'] = question.min_value
                if question.max_value is not None:
                    field_kwargs['max_value'] = question.max_value
            
            field = field_class(**field_kwargs)
            
        elif question.question_type in [Question.TYPE_RADIO, Question.TYPE_SELECT, Question.TYPE_CHECKBOX, Question.TYPE_RATING]:
            if question.question_type == Question.TYPE_RATING:
                # For rating, create choices from min to max value
                min_val = int(question.min_value) if question.min_value is not None else 1
                max_val = int(question.max_value) if question.max_value is not None else 5
                choices = [(str(i), str(i)) for i in range(min_val, max_val + 1)]
            else:
                # For other types, get options from the related QuestionOption model
                choices = [(opt.value, opt.text) for opt in question.get_options()]
            
            if question.question_type == Question.TYPE_RADIO:
                field = forms.ChoiceField(
                    choices=choices,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                    **field_kwargs
                )
            elif question.question_type == Question.TYPE_SELECT:
                field = forms.ChoiceField(
                    choices=[('', '---------')] + choices,
                    widget=forms.Select(attrs={'class': 'form-select'}),
                    **field_kwargs
                )
            elif question.question_type == Question.TYPE_RATING:
                field = forms.ChoiceField(
                    choices=choices,
                    widget=forms.RadioSelect(attrs={'class': 'rating-radio'}),
                    **field_kwargs
                )
            else:  # checkbox (multiple choice)
                field = forms.MultipleChoiceField(
                    choices=choices,
                    widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
                    **field_kwargs
                )
        
        elif question.question_type == 'textarea':
            field = forms.CharField(
                widget=forms.Textarea(attrs={
                    'rows': 4,
                    'class': 'form-control',
                }),
                **field_kwargs
            )
        
        elif question.question_type == 'date':
            field = forms.DateField(
                widget=forms.DateInput(attrs={'type': 'date'}),
                **field_kwargs
            )
        
        elif question.question_type == 'time':
            field = forms.TimeField(
                widget=forms.TimeInput(attrs={'type': 'time'}),
                **field_kwargs
            )
        
        elif question.question_type == 'datetime':
            field = forms.DateTimeField(
                widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
                **field_kwargs
            )
        
        else:
            # Default to text input
            field = forms.CharField(**field_kwargs)
        
        return field
    
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

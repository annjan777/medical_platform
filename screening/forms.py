from django import forms
from django.forms import ModelForm, DateTimeInput, DateInput, Textarea, ModelChoiceField
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    ScreeningType, ScreeningSession, ScreeningResult, 
    ScreeningAttachment, ScreeningReminder
)
from patients.models import Patient
from devices.models import Device
from questionnaires.models import Questionnaire

User = get_user_model()

class ScreeningTypeForm(forms.ModelForm):
    """Form for creating and updating screening types."""
    class Meta:
        model = ScreeningType
        fields = [
            'name', 'code', 'description', 'is_active', 
            'requires_doctor_review', 'recommended_frequency',
            'pre_screening_questionnaire', 'post_screening_questionnaire'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code.islower():
            raise ValidationError('Code must be in lowercase.')
        return code


class ScreeningSessionForm(forms.ModelForm):
    """Form for creating and updating screening sessions."""
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Patient model does not currently have an is_active field.
        self.fields['patient'].queryset = Patient.objects.all()
        
        # Limit screening type choices to active types
        self.fields['screening_type'].queryset = ScreeningType.objects.filter(is_active=True)
        
        # Set default scheduled date to now if creating new
        if not self.instance.pk:
            self.initial['scheduled_date'] = timezone.now()
    
    class Meta:
        model = ScreeningSession
        fields = [
            'patient', 'screening_type', 'scheduled_date', 'location', 
            'device_used',
            'consent_obtained', 'consent_text_version',
            'notes'
        ]
        widgets = {
            'scheduled_date': DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'notes': Textarea(attrs={'rows': 3}),
            'consent_text_version': Textarea(attrs={'rows': 3}),
        }
    
    def clean_scheduled_date(self):
        scheduled_date = self.cleaned_data.get('scheduled_date')
        if scheduled_date and scheduled_date < timezone.now():
            raise ValidationError('Scheduled date cannot be in the past.')
        return scheduled_date
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk:  # Only set created_by for new instances
            instance.created_by = self.user
        # Stamp consent time when consent is obtained
        if instance.consent_obtained and not instance.consented_at:
            instance.consented_at = timezone.now()
        if commit:
            instance.save()
        return instance


class ScreeningResultForm(forms.ModelForm):
    """Form for recording screening results."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields required
        self.fields['result_data'].required = True
        self.fields['findings'].required = True
    
    class Meta:
        model = ScreeningResult
        fields = [
            'result_data', 'findings', 'recommendations',
            'needs_follow_up', 'follow_up_date', 'follow_up_notes'
        ]
        widgets = {
            'result_data': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter result data in JSON format',
                'rows': 3
            }),
            'findings': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter detailed findings',
                'rows': 3
            }),
            'recommendations': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter recommendations',
                'rows': 2
            }),
            'follow_up_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter follow-up notes if needed',
                'rows': 2
            }),
            'follow_up_date': DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
        }
    
    def clean_result_data(self):
        result_data = self.cleaned_data.get('result_data')
        # Add validation for result_data if needed
        return result_data
    
    def clean(self):
        cleaned_data = super().clean()
        needs_follow_up = cleaned_data.get('needs_follow_up')
        follow_up_date = cleaned_data.get('follow_up_date')
        
        if needs_follow_up and not follow_up_date:
            self.add_error('follow_up_date', 'Follow-up date is required when follow-up is needed.')
        
        return cleaned_data


class ScreeningAttachmentForm(forms.ModelForm):
    """Form for uploading screening attachments."""
    class Meta:
        model = ScreeningAttachment
        fields = ['file', 'description', 'file_type']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of the file'
            }),
            'file_type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Add file validation here (size, type, etc.)
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                raise ValidationError('File size must be no more than 10MB.')
        return file


class ScreeningReminderForm(forms.ModelForm):
    """Form for creating and updating screening reminders."""
    class Meta:
        model = ScreeningReminder
        fields = ['reminder_type', 'scheduled_time', 'sent_via']
        widgets = {
            'scheduled_time': DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'reminder_type': forms.Select(attrs={'class': 'form-control'}),
            'sent_via': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_scheduled_time(self):
        scheduled_time = self.cleaned_data.get('scheduled_time')
        if scheduled_time and scheduled_time < timezone.now():
            raise ValidationError('Scheduled time cannot be in the past.')
        return scheduled_time

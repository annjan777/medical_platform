from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import Patient, MedicalRecord, VitalSigns, PatientNote, Document

class BaseForm(forms.ModelForm):
    """Base form class with common functionality for all forms"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Add form-control class to all fields
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'
            
            # Add placeholder
            if field.help_text and not field.widget.attrs.get('placeholder'):
                field.widget.attrs['placeholder'] = field.help_text
            
            # Add required attribute for required fields
            if field.required:
                field.widget.attrs['required'] = 'required'

class PatientForm(BaseForm):
    """Form for creating and updating Patient records"""
    class Meta:
        model = Patient
        fields = [
            'patient_id', 'first_name', 'last_name', 'date_of_birth', 'gender',
            'email', 'phone_number', 'address', 'city', 'state', 'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation'
        ]
        widgets = {
            'patient_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Auto-generated or manual',
                'readonly': True
            }),
            'date_of_birth': forms.DateInput(
                attrs={
                    'type': 'date',
                    'max': timezone.now().date().isoformat(),
                    'class': 'form-control datepicker',
                },
                format='%Y-%m-%d'
            ),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_relation': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > timezone.now().date():
            raise ValidationError(_("Date of birth cannot be in the future"))
        return dob

class MedicalRecordForm(BaseForm):
    """Form for creating and updating Medical Records"""
    class Meta:
        model = MedicalRecord
        fields = [
            'blood_type', 'height', 'weight', 'allergies',
            'current_medications', 'past_medications',
            'chronic_conditions', 'surgeries', 'family_history', 'notes'
        ]
        widgets = {
            'allergies': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'current_medications': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'past_medications': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'chronic_conditions': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'surgeries': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'family_history': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'height': forms.NumberInput(attrs={'step': '0.1', 'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'step': '0.1', 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        height = cleaned_data.get('height')
        weight = cleaned_data.get('weight')
        
        if height and height <= 0:
            self.add_error('height', _('Height must be greater than zero'))
        if weight and weight <= 0:
            self.add_error('weight', _('Weight must be greater than zero'))
            
        return cleaned_data

class VitalSignsForm(BaseForm):
    """Form for recording vital signs"""
    class Meta:
        model = VitalSigns
        fields = [
            'systolic_bp', 'diastolic_bp', 'heart_rate', 'respiratory_rate',
            'temperature', 'oxygen_saturation', 'weight', 'height', 'notes'
        ]
        widgets = {
            'systolic_bp': forms.NumberInput(attrs={'class': 'form-control'}),
            'diastolic_bp': forms.NumberInput(attrs={'class': 'form-control'}),
            'heart_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'respiratory_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'temperature': forms.NumberInput(attrs={'step': '0.1', 'class': 'form-control'}),
            'oxygen_saturation': forms.NumberInput(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'step': '0.1', 'class': 'form-control'}),
            'height': forms.NumberInput(attrs={'step': '0.1', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        systolic = cleaned_data.get('systolic_bp')
        diastolic = cleaned_data.get('diastolic_bp')
        heart_rate = cleaned_data.get('heart_rate')
        respiratory_rate = cleaned_data.get('respiratory_rate')
        temperature = cleaned_data.get('temperature')
        oxygen = cleaned_data.get('oxygen_saturation')
        weight = cleaned_data.get('weight')
        height = cleaned_data.get('height')
        
        if systolic and diastolic and systolic <= diastolic:
            self.add_error('systolic_bp', _('Systolic must be greater than diastolic'))
        
        if heart_rate and (heart_rate < 30 or heart_rate > 250):
            self.add_error('heart_rate', _('Heart rate must be between 30 and 250 bpm'))
            
        if respiratory_rate and (respiratory_rate < 5 or respiratory_rate > 60):
            self.add_error('respiratory_rate', _('Respiratory rate must be between 5 and 60 bpm'))
            
        if temperature and (temperature < 30 or temperature > 45):
            self.add_error('temperature', _('Temperature must be between 30°C and 45°C'))
            
        if oxygen and (oxygen < 0 or oxygen > 100):
            self.add_error('oxygen_saturation', _('Oxygen saturation must be between 0% and 100%'))
            
        if weight and weight <= 0:
            self.add_error('weight', _('Weight must be greater than zero'))
            
        if height and height <= 0:
            self.add_error('height', _('Height must be greater than zero'))
            
        return cleaned_data

class PatientNoteForm(BaseForm):
    """Form for adding clinical notes"""
    class Meta:
        model = PatientNote
        fields = ['note_type', 'title', 'content', 'is_important']
        widgets = {
            'note_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'is_important': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class DocumentForm(BaseForm):
    """Form for uploading patient documents"""
    class Meta:
        model = Document
        fields = ['document_type', 'title', 'description', 'file']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Limit file size to 10MB
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                raise ValidationError(_('File size must be no more than 10MB'))
            
            # Validate file types
            allowed_types = [
                'application/pdf',
                'image/jpeg',
                'image/png',
                'image/gif',
                'application/msword',  # .doc
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
                'application/vnd.ms-excel',  # .xls
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
                'text/plain',
            ]
            
            if file.content_type not in allowed_types:
                raise ValidationError(_('File type not supported. Please upload a PDF, image, or document file.'))
        
        return file

class PatientSearchForm(forms.Form):
    """Form for searching patients"""
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by name, phone, or email...'),
            'autocomplete': 'off'
        })
    )
    
    gender = forms.ChoiceField(
        required=False,
        choices=[('', _('All Genders'))] + list(Patient.Gender.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    min_age = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=150,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Min Age')
        })
    )
    
    max_age = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=150,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Max Age')
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        min_age = cleaned_data.get('min_age')
        max_age = cleaned_data.get('max_age')
        
        if min_age and max_age and min_age > max_age:
            self.add_error('max_age', _('Max age must be greater than or equal to min age'))
            
        return cleaned_data

class DateRangeForm(forms.Form):
    """Form for filtering by date range"""
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', _('End date must be after start date'))
            
        return cleaned_data

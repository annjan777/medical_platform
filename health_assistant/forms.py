from django import forms
from patients.models import Patient
from django.core.validators import RegexValidator
import re
from datetime import date


class PatientRegistrationForm(forms.ModelForm):
    """Form for patient registration"""
    
    class Meta:
        model = Patient
        fields = [
            'setu_id', 'first_name', 'last_name', 'date_of_birth', 'gender',
            'phone_number', 'email', 'address', 'city', 'state', 'postal_code'
        ]
        widgets = {
            'setu_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Setu ID (optional)'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'max': date.today().strftime('%Y-%m-%d')
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number (required)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address (required)'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Street address (optional)'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City (optional)'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State/Province (optional)'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Postal code (optional)'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make required fields clear
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['gender'].required = True
        self.fields['phone_number'].required = True  # Phone is now mandatory
        
        # Make optional fields clear
        optional_fields = [
            'date_of_birth', 'address', 'city', 
            'state', 'postal_code'
        ]
        for field in optional_fields:
            self.fields[field].required = False
        
        # Phone number validation is handled in clean_phone_number method
    
    def clean_first_name(self):
        """Validate patient first name"""
        first_name = self.cleaned_data.get('first_name')
        if not first_name or len(first_name.strip()) < 2:
            raise forms.ValidationError("First name must be at least 2 characters long.")
        
        # Remove extra whitespace
        first_name = ' '.join(first_name.split())
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r'^[a-zA-Z\s\-\'\.]+$', first_name):
            raise forms.ValidationError("First name can only contain letters, spaces, hyphens, and apostrophes.")
        
        return first_name.title()  # Convert to title case
    
    def clean_last_name(self):
        """Validate patient last name"""
        last_name = self.cleaned_data.get('last_name')
        if not last_name or len(last_name.strip()) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters long.")
        
        # Remove extra whitespace
        last_name = ' '.join(last_name.split())
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r'^[a-zA-Z\s\-\'\.]+$', last_name):
            raise forms.ValidationError("Last name can only contain letters, spaces, hyphens, and apostrophes.")
        
        return last_name.title()  # Convert to title case
    
    def clean_phone_number(self):
        """Validate phone number is exactly 10 digits"""
        phone = self.cleaned_data.get('phone_number')
        if not phone:
            raise forms.ValidationError("Phone number is mandatory.")
            
        # Remove any non-digit characters (like spaces, hyphens, parentheses)
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) != 10:
            raise forms.ValidationError(f"Phone number must be exactly 10 digits. You entered {len(digits)} digits.")
            
        return digits
    
    def clean_date_of_birth(self):
        """Validate date of birth"""
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            if dob > date.today():
                raise forms.ValidationError("Date of birth cannot be in the future.")
            
            # Check if age is reasonable
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age > 150:
                raise forms.ValidationError("Date of birth seems unrealistic. Please verify.")
        
        return dob
    
    def save(self, commit=True):
        """Override save to handle additional logic"""
        patient = super().save(commit=False)
        
        if commit:
            patient.save()
        
        return patient


class PatientSearchForm(forms.Form):
    """Form for searching patients"""
    query = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, ID, or phone...'
        })
    )


class ScreeningSessionFilterForm(forms.Form):
    """Form for filtering screening sessions"""
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed')
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean(self):
        """Validate date range"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Start date cannot be after end date.")
        
        return cleaned_data

from patients.models import Patient, PatientVitals

class VitalsForm(forms.ModelForm):
    """Form for collecting patient vitals"""
    
    class Meta:
        model = PatientVitals
        fields = [
            'weight', 'height', 'blood_pressure_systolic', 
            'blood_pressure_diastolic', 'heart_rate', 
            'temperature', 'spo2', 'respiratory_rate'
        ]
        labels = {
            'respiratory_rate': 'Respiratory Rate (BPM)',
        }
        widgets = {
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Weight (kg)'}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Height (cm)'}),
            'blood_pressure_systolic': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Systolic (mmHg)'}),
            'blood_pressure_diastolic': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Diastolic (mmHg)'}),
            'heart_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Heart Rate (bpm)'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Temp (°C)'}),
            'spo2': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'SpO2 (%)', 'min': '0', 'max': '100'}),
            'respiratory_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'BPM'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # For simplicity in this demo flow, all vitals can be optional,
        # but we can enforce some if needed.
        for field in self.fields:
            self.fields[field].required = False

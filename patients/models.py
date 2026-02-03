from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Patient(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')
        OTHER = 'O', _('Other')
        UNSPECIFIED = 'U', _('Prefer not to say')
    
    # Auto-generated patient ID (nullable for migration)
    patient_id = models.CharField(_('patient ID'), max_length=20, unique=True, null=True, blank=True)
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_profile'
    )
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    date_of_birth = models.DateField(_('date of birth'))
    gender = models.CharField(
        _('gender'),
        max_length=1,
        choices=Gender.choices,
        default=Gender.UNSPECIFIED
    )
    phone_number = models.CharField(_('phone number'), max_length=20, blank=True)
    email = models.EmailField(_('email address'), blank=True)
    address = models.TextField(_('address'), blank=True)
    city = models.CharField(_('city'), max_length=100, blank=True)
    state = models.CharField(_('state/province'), max_length=100, blank=True)
    postal_code = models.CharField(_('postal code'), max_length=20, blank=True)
    country = models.CharField(_('country'), max_length=100, blank=True)
    emergency_contact_name = models.CharField(_('emergency contact name'), max_length=200, blank=True)
    emergency_contact_phone = models.CharField(_('emergency contact phone'), max_length=20, blank=True)
    emergency_contact_relation = models.CharField(_('relation to patient'), max_length=100, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_patients',
    )
    
    class Meta:
        ordering = ['patient_id']
        verbose_name = _('patient')
        verbose_name_plural = _('patients')
    
    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.patient_id})"
    
    def save(self, *args, **kwargs):
        # Generate patient ID if it doesn't exist
        if not self.patient_id:
            self.patient_id = self.generate_patient_id()
        super().save(*args, **kwargs)
    
    def generate_patient_id(self):
        """Generate a unique patient ID in format MDCP0001, MDCP0002, etc."""
        from django.db.models import Max
        
        # Get the highest current patient ID number
        last_patient = Patient.objects.aggregate(
            max_id=Max('patient_id')
        )['max_id']
        
        if last_patient is None:
            new_number = 1
        else:
            # Extract the numeric part from the last patient ID
            import re
            match = re.search(r'(\d+)', last_patient)
            if match:
                last_number = int(match.group(1))
                new_number = last_number + 1
            else:
                new_number = 1
        
        return f"MDCP{new_number:04d}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
        
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        return self.full_name
    
    @property
    def age(self):
        import datetime
        today = datetime.date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

class MedicalRecord(models.Model):
    patient = models.OneToOneField(
        Patient,
        on_delete=models.CASCADE,
        related_name='medical_record'
    )
    blood_type = models.CharField(_('blood type'), max_length=10, blank=True)
    height = models.DecimalField(_('height (cm)'), max_digits=5, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(_('weight (kg)'), max_digits=5, decimal_places=2, null=True, blank=True)
    bmi = models.DecimalField(_('BMI'), max_digits=5, decimal_places=2, null=True, blank=True)
    allergies = models.TextField(_('allergies'), blank=True)
    current_medications = models.TextField(_('current medications'), blank=True)
    past_medications = models.TextField(_('past medications'), blank=True)
    chronic_conditions = models.TextField(_('chronic conditions'), blank=True)
    surgeries = models.TextField(_('surgeries'), blank=True)
    family_history = models.TextField(_('family medical history'), blank=True)
    notes = models.TextField(_('additional notes'), blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('medical record')
        verbose_name_plural = _('medical records')
    
    def __str__(self):
        return f"Medical Record - {self.patient}"
    
    def save(self, *args, **kwargs):
        # Calculate BMI if height and weight are provided
        if self.height and self.weight:
            height_in_meters = float(self.height) / 100  # Convert cm to m
            self.bmi = float(self.weight) / (height_in_meters ** 2)
        super().save(*args, **kwargs)

class VitalSigns(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='vital_signs'
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_vital_signs'
    )
    systolic_bp = models.PositiveSmallIntegerField(_('systolic BP (mmHg)'), null=True, blank=True)
    diastolic_bp = models.PositiveSmallIntegerField(_('diastolic BP (mmHg)'), null=True, blank=True)
    heart_rate = models.PositiveSmallIntegerField(_('heart rate (bpm)'), null=True, blank=True)
    respiratory_rate = models.PositiveSmallIntegerField(_('respiratory rate (bpm)'), null=True, blank=True)
    temperature = models.DecimalField(_('temperature (°C)'), max_digits=3, decimal_places=1, null=True, blank=True)
    oxygen_saturation = models.PositiveSmallIntegerField(
        _('oxygen saturation (%)'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True
    )
    weight = models.DecimalField(_('weight (kg)'), max_digits=5, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(_('height (cm)'), max_digits=5, decimal_places=2, null=True, blank=True)
    bmi = models.DecimalField(_('BMI'), max_digits=5, decimal_places=2, null=True, blank=True)
    recorded_at = models.DateTimeField(_('recorded at'), auto_now_add=True)
    notes = models.TextField(_('notes'), blank=True)
    
    class Meta:
        ordering = ['-recorded_at']
        verbose_name = _('vital signs')
        verbose_name_plural = _('vital signs')
    
    def __str__(self):
        return f"Vital Signs - {self.patient} at {self.recorded_at}"
    
    def save(self, *args, **kwargs):
        # Calculate BMI if height and weight are provided
        if self.height and self.weight:
            height_in_meters = float(self.height) / 100  # Convert cm to m
            self.bmi = float(self.weight) / (height_in_meters ** 2)
        super().save(*args, **kwargs)

class PatientNote(models.Model):
    class NoteType(models.TextChoices):
        GENERAL = 'GENERAL', _('General Note')
        CONSULTATION = 'CONSULTATION', _('Consultation')
        FOLLOW_UP = 'FOLLOW_UP', _('Follow-up')
        TREATMENT = 'TREATMENT', _('Treatment')
        OTHER = 'OTHER', _('Other')
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='patient_notes'
    )
    note_type = models.CharField(
        _('note type'),
        max_length=20,
        choices=NoteType.choices,
        default=NoteType.GENERAL
    )
    title = models.CharField(_('title'), max_length=200)
    content = models.TextField(_('content'))
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    is_important = models.BooleanField(_('important'), default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('patient note')
        verbose_name_plural = _('patient notes')
    
    def __str__(self):
        return f"{self.get_note_type_display()} - {self.patient} - {self.title}"

class Document(models.Model):
    class DocumentType(models.TextChoices):
        PRESCRIPTION = 'PRESCRIPTION', _('Prescription')
        REPORT = 'REPORT', _('Medical Report')
        SCAN = 'SCAN', _('Scan/Image')
        LAB_RESULT = 'LAB_RESULT', _('Lab Result')
        OTHER = 'OTHER', _('Other')
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    document_type = models.CharField(
        _('document type'),
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.OTHER
    )
    title = models.CharField(_('title'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    file = models.FileField(_('file'), upload_to='patient_documents/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = _('document')
        verbose_name_plural = _('documents')
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.patient} - {self.title}"
    
    def file_extension(self):
        import os
        name, extension = os.path.splitext(self.file.name)
        return extension.lower()
    
    def is_image(self):
        return self.file_extension() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
    
    def is_pdf(self):
        return self.file_extension() == '.pdf'

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class ScreeningType(models.Model):
    """Model representing different types of screenings (e.g., diabetes, hypertension)."""
    
    name = models.CharField(max_length=100, unique=True)
    code = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    requires_doctor_review = models.BooleanField(default=False)
    
    # Screening frequency in days (0 for one-time screenings)
    recommended_frequency = models.PositiveIntegerField(
        default=0,
        help_text="Recommended days between screenings (0 for one-time screenings)"
    )
    
    # Related questionnaires
    pre_screening_questionnaire = models.ForeignKey(
        'questionnaires.Questionnaire',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pre_screening_types',
        help_text="Questionnaire to be completed before screening"
    )
    
    post_screening_questionnaire = models.ForeignKey(
        'questionnaires.Questionnaire',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='post_screening_types',
        help_text="Questionnaire to be completed after screening"
    )

    # Supported device types for this screening product (SRS)
    # Stores values from devices.Device.DEVICE_TYPES (e.g., "oximeter", "ecg")
    supported_device_types = models.JSONField(
        default=list,
        blank=True,
        help_text='List of supported device_type values for this screening type'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'screening type'
        verbose_name_plural = 'screening types'
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('screening:type_detail', args=[str(self.id)])


class ScreeningSession(models.Model):
    """Model representing a screening session for a patient."""
    
    # Status choices
    STATUS_SCHEDULED = 'scheduled'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_RESCHEDULED = 'rescheduled'
    
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_RESCHEDULED, 'Rescheduled'),
    ]
    
    # Result status
    RESULT_NORMAL = 'normal'
    RESULT_ABNORMAL = 'abnormal'
    RESULT_INCONCLUSIVE = 'inconclusive'
    RESULT_PENDING = 'pending'
    
    RESULT_CHOICES = [
        (RESULT_NORMAL, 'Normal'),
        (RESULT_ABNORMAL, 'Abnormal'),
        (RESULT_INCONCLUSIVE, 'Inconclusive'),
        (RESULT_PENDING, 'Pending Review'),
    ]
    
    # Basic information
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='screening_sessions'
    )
    
    screening_type = models.ForeignKey(
        ScreeningType,
        on_delete=models.PROTECT,
        related_name='sessions'
    )
    
    # Session details
    scheduled_date = models.DateTimeField()
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED
    )
    
    result_status = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        default=RESULT_PENDING
    )
    
    # Staff involved
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_screenings'
    )
    
    conducted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conducted_screenings'
    )
    
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_screenings'
    )
    
    # Related data
    device_used = models.ForeignKey(
        'devices.Device',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='screening_sessions'
    )

    # Consent capture (SRS)
    consent_obtained = models.BooleanField(default=False)
    consent_text_version = models.TextField(
        blank=True,
        help_text='Consent text/version shown to the patient (store immutably per session)'
    )
    consented_at = models.DateTimeField(null=True, blank=True)
    
    # Location information
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_date']
        verbose_name = 'screening session'
        verbose_name_plural = 'screening sessions'
    
    def __str__(self):
        return f"{self.patient} - {self.screening_type} - {self.get_status_display()}"
    
    def get_absolute_url(self):
        return reverse('screening:session_detail', args=[str(self.id)])
    
    @property
    def duration(self):
        """Calculate the duration of the screening session in minutes."""
        if self.actual_start_time and self.actual_end_time:
            duration = self.actual_end_time - self.actual_start_time
            return round(duration.total_seconds() / 60, 2)
        return None
    
    def is_overdue(self):
        """Check if the screening is overdue."""
        if self.status in [self.STATUS_COMPLETED, self.STATUS_CANCELLED]:
            return False
        return timezone.now() > self.scheduled_date
    
    def can_start(self):
        """Check if the screening can be started."""
        return self.status == self.STATUS_SCHEDULED
    
    def can_complete(self):
        """Check if the screening can be marked as completed."""
        return self.status == self.STATUS_IN_PROGRESS
    
    def get_questionnaire_responses(self):
        """Get all questionnaire responses associated with this screening."""
        from questionnaires.models import Response
        return Response.objects.filter(session=self)


class ScreeningResult(models.Model):
    """Model to store detailed results of a screening session."""
    
    session = models.OneToOneField(
        ScreeningSession,
        on_delete=models.CASCADE,
        related_name='screening_result'
    )
    
    # Results data (structure depends on screening type)
    result_data = models.JSONField()
    
    # Medical professional's notes
    findings = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    
    # Follow-up information
    needs_follow_up = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'screening result'
        verbose_name_plural = 'screening results'
    
    def __str__(self):
        return f"Results for {self.session}"


class ScreeningAttachment(models.Model):
    """Model to store files/images related to a screening session."""
    
    session = models.ForeignKey(
        ScreeningSession,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    file = models.FileField(upload_to='screening_attachments/%Y/%m/%d/')
    file_type = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'screening attachment'
        verbose_name_plural = 'screening attachments'
    
    def __str__(self):
        return f"{self.file.name} - {self.session}"


class ScreeningReminder(models.Model):
    """Model to track reminders for upcoming or due screenings."""
    
    REMINDER_TYPE_UPCOMING = 'upcoming'
    REMINDER_TYPE_OVERDUE = 'overdue'
    REMINDER_TYPE_FOLLOW_UP = 'follow_up'
    
    REMINDER_TYPES = [
        (REMINDER_TYPE_UPCOMING, 'Upcoming Screening'),
        (REMINDER_TYPE_OVERDUE, 'Overdue Screening'),
        (REMINDER_TYPE_FOLLOW_UP, 'Follow-up Required'),
    ]
    
    session = models.ForeignKey(
        ScreeningSession,
        on_delete=models.CASCADE,
        related_name='reminders'
    )
    
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    scheduled_time = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_via = models.CharField(max_length=50, blank=True)  # email, sms, push, etc.
    
    # For tracking if the reminder was successful
    is_sent = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-scheduled_time']
        verbose_name = 'screening reminder'
        verbose_name_plural = 'screening reminders'
    
    def __str__(self):
        return f"{self.get_reminder_type_display()} - {self.session}"
    
    def is_due(self):
        """Check if the reminder is due to be sent."""
        return not self.is_sent and timezone.now() >= self.scheduled_time

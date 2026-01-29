from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

User = get_user_model()

class Device(models.Model):
    """Model representing a medical device in the system."""
    
    # Device status choices
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_MAINTENANCE = 'maintenance'
    STATUS_RETIRED = 'retired'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_MAINTENANCE, 'Under Maintenance'),
        (STATUS_RETIRED, 'Retired'),
    ]
    
    # Device type choices
    TYPE_BP_MONITOR = 'bp_monitor'
    TYPE_GLUCOMETER = 'glucometer'
    TYPE_WEIGHT_SCALE = 'weight_scale'
    TYPE_THERMOMETER = 'thermometer'
    TYPE_OXIMETER = 'oximeter'
    TYPE_ECG = 'ecg'
    TYPE_OTHER = 'other'
    
    DEVICE_TYPES = [
        (TYPE_BP_MONITOR, 'Blood Pressure Monitor'),
        (TYPE_GLUCOMETER, 'Glucometer'),
        (TYPE_WEIGHT_SCALE, 'Weight Scale'),
        (TYPE_THERMOMETER, 'Thermometer'),
        (TYPE_OXIMETER, 'Pulse Oximeter'),
        (TYPE_ECG, 'ECG Device'),
        (TYPE_OTHER, 'Other'),
    ]
    
    # Device identification
    name = models.CharField(max_length=100, help_text='Device display name')
    device_id = models.CharField(
        max_length=100, 
        unique=True,
        help_text='Unique device identifier (serial number or MAC address)'
    )
    device_type = models.CharField(
        max_length=20, 
        choices=DEVICE_TYPES,
        default=TYPE_OTHER,
        help_text='Type of medical device'
    )
    manufacturer = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=50, blank=True)
    firmware_version = models.CharField(max_length=50, blank=True)
    
    # Device status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_INACTIVE,
        help_text='Current status of the device'
    )

    # Real-world connectivity / availability (SRS)
    CONNECTION_UNKNOWN = 'unknown'
    CONNECTION_CONNECTED = 'connected'
    CONNECTION_DISCONNECTED = 'disconnected'
    CONNECTION_CHOICES = [
        (CONNECTION_UNKNOWN, 'Unknown'),
        (CONNECTION_CONNECTED, 'Connected'),
        (CONNECTION_DISCONNECTED, 'Disconnected'),
    ]

    connection_status = models.CharField(
        max_length=20,
        choices=CONNECTION_CHOICES,
        default=CONNECTION_UNKNOWN,
        help_text='Connectivity status (from heartbeat/agent)'
    )
    last_heartbeat_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last heartbeat timestamp received from device/gateway'
    )
    is_busy = models.BooleanField(
        default=False,
        help_text='Whether the device is currently busy (in an active session)'
    )
    is_locked = models.BooleanField(
        default=False,
        help_text='Whether the device is locked for an active screening session'
    )
    locked_session_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Screening session identifier that holds the lock (if any)'
    )
    last_calibration_date = models.DateField(null=True, blank=True)
    next_calibration_date = models.DateField(null=True, blank=True)
    
    # Device assignment
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_devices',
        help_text='User currently assigned to this device'
    )
    location = models.CharField(
        max_length=200, 
        blank=True,
        help_text='Physical location of the device'
    )
    
    # Timestamps
    date_added = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Additional information
    description = models.TextField(blank=True, help_text='Additional notes about the device')
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this device should be treated as active.'
    )
    
    class Meta:
        ordering = ['device_type', 'name']
        verbose_name = 'device'
        verbose_name_plural = 'devices'
    
    def __str__(self):
        return f"{self.get_device_type_display()}: {self.name} ({self.device_id})"
    
    def get_absolute_url(self):
        return reverse('devices:device_detail', args=[str(self.id)])
    
    def is_available(self):
        """Check if the device is available for assignment."""
        return self.status == self.STATUS_ACTIVE and not self.assigned_to
    
    def needs_calibration(self):
        """Check if the device is due for calibration."""
        if not self.next_calibration_date:
            return False
        return self.next_calibration_date <= timezone.now().date()
    
    def get_usage_stats(self):
        """Get usage statistics for the device."""
        # This would be implemented to return usage statistics
        return {
            'total_readings': 0,  # Placeholder
            'last_used': None,    # Placeholder
        }


class DeviceReading(models.Model):
    """Model to store readings from medical devices."""
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='readings',
        help_text='Device that generated this reading'
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='device_readings',
        help_text='Patient this reading belongs to'
    )
    reading_type = models.CharField(
        max_length=50,
        help_text='Type of reading (e.g., blood_pressure, blood_glucose)'
    )
    reading_data = models.JSONField(
        help_text='Structured data for the reading (format depends on device type)'
    )
    recorded_at = models.DateTimeField(
        default=timezone.now,
        help_text='When the reading was taken'
    )
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text='User who recorded this reading'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-recorded_at']
        verbose_name = 'device reading'
        verbose_name_plural = 'device readings'
    
    def __str__(self):
        return f"{self.reading_type} reading for {self.patient} at {self.recorded_at}"

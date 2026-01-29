from rest_framework import serializers
from .models import (
    ScreeningType, ScreeningSession, ScreeningResult, 
    ScreeningAttachment, ScreeningReminder
)

class ScreeningTypeSerializer(serializers.ModelSerializer):
    """Serializer for ScreeningType model."""
    class Meta:
        model = ScreeningType
        fields = [
            'id', 'name', 'code', 'description', 'is_active',
            'requires_doctor_review', 'recommended_frequency',
            'pre_screening_questionnaire', 'post_screening_questionnaire',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class ScreeningSessionSerializer(serializers.ModelSerializer):
    """Serializer for ScreeningSession model."""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    screening_type_name = serializers.CharField(source='screening_type.name', read_only=True)
    conducted_by_name = serializers.CharField(source='conducted_by.get_full_name', read_only=True)
    
    class Meta:
        model = ScreeningSession
        fields = [
            'id', 'patient', 'patient_name', 'screening_type', 'screening_type_name',
            'scheduled_date', 'actual_start_time', 'actual_end_time', 'status',
            'result_status', 'conducted_by', 'conducted_by_name', 'device_used',
            'location', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'actual_start_time', 
            'actual_end_time', 'status', 'result_status'
        ]

class ScreeningResultSerializer(serializers.ModelSerializer):
    """Serializer for ScreeningResult model."""
    class Meta:
        model = ScreeningResult
        fields = [
            'id', 'session', 'result_data', 'findings', 'recommendations',
            'needs_follow_up', 'follow_up_date', 'follow_up_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class ScreeningAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for ScreeningAttachment model."""
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ScreeningAttachment
        fields = [
            'id', 'session', 'file', 'file_url', 'file_name', 
            'file_type', 'description', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None
    
    def get_file_name(self, obj):
        if obj.file:
            return obj.file.name.split('/')[-1]
        return None

class ScreeningReminderSerializer(serializers.ModelSerializer):
    """Serializer for ScreeningReminder model."""
    class Meta:
        model = ScreeningReminder
        fields = [
            'id', 'session', 'reminder_type', 'scheduled_time',
            'sent_at', 'sent_via', 'is_sent', 'error_message', 'created_at'
        ]
        read_only_fields = ['created_at', 'sent_at', 'is_sent', 'error_message']

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Patient, MedicalRecord, VitalSigns, PatientNote, Document

class MedicalRecordInline(admin.StackedInline):
    model = MedicalRecord
    can_delete = False
    extra = 0
    fields = ('blood_type', 'height', 'weight', 'bmi', 'allergies', 'current_medications')
    readonly_fields = ('bmi',)
    show_change_link = True

class VitalSignsInline(admin.TabularInline):
    model = VitalSigns
    extra = 1
    fields = ('recorded_at', 'systolic_bp', 'diastolic_bp', 'heart_rate', 'temperature', 'oxygen_saturation')
    readonly_fields = ('recorded_at', 'bmi')

class PatientNoteInline(admin.TabularInline):
    model = PatientNote
    extra = 1
    fields = ('created_at', 'note_type', 'title', 'is_important')
    readonly_fields = ('created_at',)

class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1
    fields = ('title', 'document_type', 'uploaded_at', 'file_link')
    readonly_fields = ('uploaded_at', 'file_link')
    
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View File</a>', obj.file.url)
        return "-"
    file_link.short_description = 'File'

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'age', 'gender', 'phone_number', 'email', 'city', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone_number', 'email', 'city', 'emergency_contact_name')
    list_filter = ('gender', 'city', 'created_at')
    readonly_fields = ('age', 'created_at', 'updated_at')
    fieldsets = (
        ('Personal Information', {
            'fields': (('first_name', 'last_name'), 'date_of_birth', 'gender', 'email', 'phone_number')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'postal_code', 'country')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('user', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [MedicalRecordInline, VitalSignsInline, PatientNoteInline, DocumentInline]
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'blood_type', 'bmi', 'updated_at')
    search_fields = ('patient__first_name', 'patient__last_name', 'blood_type')
    list_filter = ('blood_type', 'updated_at')
    readonly_fields = ('bmi', 'created_at', 'updated_at')
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient',)
        }),
        ('Medical Information', {
            'fields': ('blood_type', 'height', 'weight', 'bmi', 'allergies')
        }),
        ('Medical History', {
            'fields': ('current_medications', 'past_medications', 'chronic_conditions', 'surgeries', 'family_history')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(VitalSigns)
class VitalSignsAdmin(admin.ModelAdmin):
    list_display = ('patient', 'recorded_at', 'systolic_bp', 'diastolic_bp', 'heart_rate', 'temperature', 'oxygen_saturation')
    search_fields = ('patient__first_name', 'patient__last_name', 'notes')
    list_filter = ('recorded_at',)
    readonly_fields = ('bmi', 'recorded_at')
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient', 'recorded_by', 'recorded_at')
        }),
        ('Vital Signs', {
            'fields': (
                ('systolic_bp', 'diastolic_bp'),
                'heart_rate',
                'respiratory_rate',
                'temperature',
                'oxygen_saturation',
                ('height', 'weight', 'bmi')
            )
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(PatientNote)
class PatientNoteAdmin(admin.ModelAdmin):
    list_display = ('patient', 'title', 'note_type', 'author', 'created_at', 'is_important')
    search_fields = ('patient__first_name', 'patient__last_name', 'title', 'content')
    list_filter = ('note_type', 'is_important', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Note Information', {
            'fields': ('patient', 'author', 'note_type', 'title', 'is_important')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        super().save_model(request, obj, form, change)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'patient', 'document_type', 'uploaded_at', 'file_link')
    search_fields = ('patient__first_name', 'patient__last_name', 'title', 'description')
    list_filter = ('document_type', 'uploaded_at')
    readonly_fields = ('uploaded_at', 'file_link')
    fieldsets = (
        ('Document Information', {
            'fields': ('patient', 'uploaded_by', 'document_type', 'title', 'description')
        }),
        ('File', {
            'fields': ('file', 'file_link')
        }),
        ('System Information', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )
    
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View File</a>', obj.file.url)
        return "-"
    file_link.short_description = 'File'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

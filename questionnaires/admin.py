from django.contrib import admin
from django.http import HttpResponse
import csv
from datetime import datetime
from django import forms

from .models import Questionnaire, Question, QuestionOption, Response, Answer


@admin.action(description='Export selected questionnaire responses to CSV')
def export_responses_to_csv(modeladmin, request, queryset):
    """
    Export questionnaire responses to CSV format
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="questionnaire_responses_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Response ID', 'Patient ID', 'Patient Name', 'Questionnaire Title', 
        'Respondent', 'Date Created', 'Is Complete', 'Question', 'Answer'
    ])
    
    # Write data
    for resp in queryset:
        answers = Answer.objects.filter(response=resp).order_by('question__order')
        for answer in answers:
            answer_text = answer.text_answer
            if answer.option_answer.exists():
                option = answer.option_answer.first()
                answer_text = option.text if option else answer_text
            
            writer.writerow([
                resp.id,
                resp.patient.patient_id if resp.patient else 'N/A',
                resp.patient.name if resp.patient else 'N/A',
                resp.questionnaire.title,
                resp.respondent.username if resp.respondent else 'N/A',
                resp.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                resp.is_complete,
                answer.question.question_text,
                answer_text
            ])
    
    return response


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 1
    ordering = ['order']


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    ordering = ['order']


@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'questionnaire_type', 'is_active', 'created_by', 'created_at']
    list_filter = ['status', 'questionnaire_type', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [QuestionInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'question_type', 'is_required', 'questionnaire', 'order']
    list_filter = ['question_type', 'is_required', 'questionnaire']
    search_fields = ['question_text']
    inlines = [QuestionOptionInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('questionnaire')


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = [
        'get_patient_id', 'get_patient_name', 'questionnaire', 'respondent', 
        'get_completion_status', 'get_response_time', 'submitted_at'
    ]
    list_filter = [
        'is_complete', 'questionnaire', 'submitted_at', 
        'started_at', 'respondent__role'
    ]
    search_fields = [
        'patient__patient_id', 'patient__first_name', 'patient__last_name',
        'questionnaire__title', 'respondent__username'
    ]
    readonly_fields = [
        'started_at', 'submitted_at', 'ip_address', 'user_agent',
        'get_answer_count', 'get_completion_percentage'
    ]
    actions = [export_responses_to_csv]
    
    fieldsets = (
        ('Response Information', {
            'fields': (
                'questionnaire', 'patient', 'respondent', 'is_complete',
                'started_at', 'submitted_at'
            )
        }),
        ('Technical Details', {
            'fields': (
                'ip_address', 'user_agent', 'session'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                'get_answer_count', 'get_completion_percentage'
            ),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'patient', 'questionnaire', 'respondent'
        ).prefetch_related('answers')
    
    def get_patient_id(self, obj):
        if obj.patient:
            return obj.patient.patient_id
        return 'N/A'
    get_patient_id.short_description = 'Patient ID'
    get_patient_id.admin_order_field = 'patient__patient_id'
    
    def get_patient_name(self, obj):
        if obj.patient:
            return f"{obj.patient.first_name} {obj.patient.last_name}"
        return 'No Patient'
    get_patient_name.short_description = 'Patient Name'
    get_patient_name.admin_order_field = 'patient__last_name'
    
    def get_completion_status(self, obj):
        if obj.is_complete:
            return 'Complete'
        return 'In Progress'
    get_completion_status.short_description = 'Status'
    
    def get_response_time(self, obj):
        if obj.started_at and obj.submitted_at:
            duration = obj.submitted_at - obj.started_at
            total_seconds = int(duration.total_seconds())
            if total_seconds < 60:
                return f"{total_seconds}s"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                return f"{minutes}m"
            else:
                hours = total_seconds // 3600
                return f"{hours}h"
        return 'N/A'
    get_response_time.short_description = 'Duration'
    
    def get_answer_count(self, obj):
        return obj.answers.count()
    get_answer_count.short_description = 'Answers'
    
    def get_completion_percentage(self, obj):
        total_questions = obj.questionnaire.questions.count()
        answered_questions = obj.answers.count()
        if total_questions > 0:
            percentage = (answered_questions / total_questions) * 100
            return f"{percentage:.1f}%"
        return 'N/A'
    get_completion_percentage.short_description = 'Completion %'
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'export_responses_to_csv' in actions:
            # Customize the export action name
            actions['export_responses_to_csv'] = (
                actions['export_responses_to_csv'][0],
                'Export selected responses to CSV with patient details'
            )
        return actions


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = [
        'get_patient_info', 'question', 'get_answer_text', 
        'response', 'created_at'
    ]
    list_filter = [
        'created_at', 'question__question_type', 
        'question__questionnaire', 'response__is_complete'
    ]
    search_fields = [
        'text_answer', 'question__question_text', 
        'response__patient__patient_id', 'response__patient__first_name',
        'response__patient__last_name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'response', 'question', 'response__patient', 'response__questionnaire'
        )
    
    def get_patient_info(self, obj):
        if obj.response.patient:
            patient = obj.response.patient
            return f"{patient.patient_id} - {patient.first_name} {patient.last_name}"
        return 'No Patient'
    get_patient_info.short_description = 'Patient'
    
    def get_answer_text(self, obj):
        if obj.text_answer:
            return obj.text_answer[:50] + ('...' if len(obj.text_answer) > 50 else '')
        elif obj.option_answer.exists():
            option = obj.option_answer.first()
            return option.text[:50] + ('...' if len(option.text) > 50 else '')
        return 'No Answer'
    get_answer_text.short_description = 'Answer'

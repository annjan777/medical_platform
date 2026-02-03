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
                resp.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if resp.submitted_at else resp.started_at.strftime('%Y-%m-%d %H:%M:%S'),
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
    list_display = ['id', 'patient', 'questionnaire', 'respondent', 'is_complete', 'submitted_at']
    list_filter = ['is_complete', 'questionnaire', 'submitted_at']
    search_fields = ['patient__patient_id', 'patient__name', 'questionnaire__title', 'respondent__username']
    readonly_fields = ['started_at', 'submitted_at', 'ip_address', 'user_agent']
    actions = [export_responses_to_csv]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'questionnaire', 'respondent')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['response', 'question', 'text_answer', 'created_at']
    list_filter = ['created_at', 'question__question_type']
    search_fields = ['text_answer', 'question__question_text', 'response__patient__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('response', 'question')

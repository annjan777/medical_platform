from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Questionnaire, Question, QuestionOption

class QuestionnaireBuilderView(LoginRequiredMixin, CreateView):
    """View for creating questionnaires with the simplified builder."""
    model = Questionnaire
    template_name = 'questionnaires/questionnaire_builder.html'
    fields = ['title', 'description']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create Questionnaire'
        return context
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

@login_required
@require_POST
@csrf_exempt
def save_questionnaire_api(request):
    """API endpoint to save questionnaire with questions and options."""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if 'title' not in data or not data['title'].strip():
            return JsonResponse({
                'success': False,
                'error': 'Title is required'
            }, status=400)
        
        if 'questions' not in data or not data['questions']:
            return JsonResponse({
                'success': False,
                'error': 'At least one question is required'
            }, status=400)
        
        # Validate each question
        for i, question_data in enumerate(data['questions']):
            if 'question_text' not in question_data or not question_data['question_text'].strip():
                return JsonResponse({
                    'success': False,
                    'error': f'Question {i+1}: Question text is required'
                }, status=400)
            
            if 'type' not in question_data:
                return JsonResponse({
                    'success': False,
                    'error': f'Question {i+1}: Question type is required'
                }, status=400)
        
        # Create questionnaire
        questionnaire = Questionnaire.objects.create(
            title=data['title'],
            description=data.get('description', ''),
            created_by=request.user,
            status='draft'
        )
        
        # Create questions
        # We need to map frontend IDs to database Question objects to link parents
        question_map = {}
        
        for question_data in data['questions']:
            question = Question.objects.create(
                questionnaire=questionnaire,
                question_text=question_data['question_text'],
                question_type=question_data['type'],
                is_required=question_data['required'],
                order=question_data['order']
            )
            
            # Map the frontend ID (used as internal reference) to the created question
            frontend_id = question_data.get('id')
            if frontend_id is not None:
                question_map[str(frontend_id)] = question
                
        # Second pass to set parent relationships
        for question_data in data['questions']:
            frontend_id = question_data.get('id')
            parent_id = question_data.get('parent_id')
            trigger_answer = question_data.get('trigger_answer')
            
            if frontend_id is not None and parent_id is not None and str(parent_id) in question_map:
                question = question_map[str(frontend_id)]
                question.parent = question_map[str(parent_id)]
                question.trigger_answer = trigger_answer
                question.save()
            
            # Create options for multiple choice questions
            if question_data['type'] == 'multiple_choice':
                # We need the saved question object
                question = question_map.get(str(frontend_id)) if frontend_id is not None else Question.objects.filter(questionnaire=questionnaire, order=question_data['order']).first()
                if question:
                    for option_data in question_data['options']:
                        QuestionOption.objects.create(
                            question=question,
                            text=option_data.get('text', ''),
                            order=option_data['order']
                        )
        
        return JsonResponse({
            'success': True,
            'questionnaire_id': questionnaire.id,
            'message': 'Questionnaire saved successfully!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def questionnaire_list_builder(request):
    """List view for questionnaires with builder interface."""
    questionnaires = Questionnaire.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'questionnaires/questionnaire_list_builder.html', {
        'questionnaires': questionnaires
    })

@login_required
def edit_questionnaire_builder(request, pk):
    """Edit existing questionnaire with builder interface."""
    questionnaire = get_object_or_404(Questionnaire, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        # Handle saving edited questionnaire
        try:
            data = json.loads(request.body)
            
            # Update questionnaire
            questionnaire.title = data['title']
            questionnaire.description = data.get('description', '')
            questionnaire.save()
            
            # Delete existing questions and options
            Question.objects.filter(questionnaire=questionnaire).delete()
            
            # Map frontend IDs to database Question objects to link parents
            question_map = {}
            
            # Create new questions
            for question_data in data['questions']:
                question = Question.objects.create(
                    questionnaire=questionnaire,
                    question_text=question_data['question_text'],
                    question_type=question_data['type'],
                    is_required=question_data['required'],
                    order=question_data['order']
                )
                
                frontend_id = question_data.get('id')
                if frontend_id is not None:
                    question_map[str(frontend_id)] = question
                    
            # Second pass to set parent relationships
            for question_data in data['questions']:
                frontend_id = question_data.get('id')
                parent_id = question_data.get('parent_id')
                trigger_answer = question_data.get('trigger_answer')
                
                if frontend_id is not None and parent_id is not None and str(parent_id) in question_map:
                    question = question_map[str(frontend_id)]
                    question.parent = question_map[str(parent_id)]
                    question.trigger_answer = trigger_answer
                    question.save()
                
                # Create options for multiple choice questions
                if question_data['type'] == 'multiple_choice':
                    question = question_map.get(str(frontend_id)) if frontend_id is not None else Question.objects.filter(questionnaire=questionnaire, order=question_data['order']).last()
                    if question:
                        for option_data in question_data['options']:
                            QuestionOption.objects.create(
                                question=question,
                                text=option_data.get('text', ''),
                                order=option_data['order']
                            )
            
            return JsonResponse({
                'success': True,
                'message': 'Questionnaire updated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    # GET request - show edit form
    questions_data = []
    
    # Send root questions first or order by order to rebuild logically
    all_questions = list(questionnaire.questions.all().order_by('order', 'id'))
    
    for question in all_questions:
        question_data = {
            'id': question.id,
            'question_text': question.question_text,
            'type': question.question_type,
            'required': question.is_required,
            'order': question.order,
            'parent_id': question.parent_id if question.parent else None,
            'trigger_answer': question.trigger_answer,
            'display_number': question.get_display_number()
        }
        
        if question.question_type == 'multiple_choice':
            question_data['options'] = [
                {
                    'text': opt.text,
                    'order': opt.order
                }
                for opt in question.options.all()
            ]
        
        questions_data.append(question_data)
    
    return render(request, 'questionnaires/questionnaire_builder.html', {
        'questionnaire': questionnaire,
        'questions_data': json.dumps(questions_data),
        'page_title': 'Edit Questionnaire'
    })

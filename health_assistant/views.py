from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.urls import reverse_lazy

from accounts.models import User
from patients.models import Patient
from screening.models import ScreeningSession, ScreeningType
from devices.models import Device
from questionnaires.models import Questionnaire
from .forms import PatientRegistrationForm


def format_time_diff(dt):
    """Format time difference for display"""
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


class HealthAssistantRequiredMixin(LoginRequiredMixin):
    """Mixin to ensure user is a health assistant"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != User.Role.HEALTH_ASSISTANT:
            messages.error(request, 'Access denied. Health assistant role required.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


class HealthAssistantDashboardView(HealthAssistantRequiredMixin, TemplateView):
    template_name = 'health_assistant/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get today's statistics
        today = timezone.now().date()
        todays_sessions = ScreeningSession.objects.filter(
            created_by=user,
            created_at__date=today
        )
        
        context['todays_sessions'] = todays_sessions.count()
        context['completed_sessions'] = todays_sessions.filter(status='completed').count()
        context['pending_sessions'] = todays_sessions.filter(status='in_progress').count()
        
        # Total patients this health assistant has worked with
        context['total_patients'] = Patient.objects.filter(
            screening_sessions__created_by=user
        ).distinct().count()
        
        # Recent sessions
        context['recent_sessions'] = ScreeningSession.objects.filter(
            created_by=user
        ).select_related('patient', 'screening_type').order_by('-created_at')[:10]
        
        # Device status
        context['devices'] = Device.objects.filter(status=Device.STATUS_ACTIVE).order_by('name')
        
        # System alerts (placeholder for now)
        context['alerts'] = []
        
        return context


@login_required
def home_page(request):
    """Dedicated health assistant home page with AdminLTE"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        messages.error(request, 'Access denied. Health assistant role required.')
        return redirect('login')
    
    return render(request, 'health_assistant/home_clean.html')


@login_required
def questionnaires_page(request):
    """Dedicated page for viewing available questionnaires with AdminLTE"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        messages.error(request, 'Access denied. Health assistant role required.')
        return redirect('login')
    
    return render(request, 'health_assistant/questionnaires.html')


@login_required
def landing_page(request):
    """Dedicated landing page for patient registration and questionnaire workflow with AdminLTE"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        messages.error(request, 'Access denied. Health assistant role required.')
        return redirect('login')
    
    return render(request, 'health_assistant/landing.html')


@login_required
def patient_register(request):
    """Handle patient registration"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        messages.error(request, 'Access denied. Health assistant role required.')
        return redirect('login')
    
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient {patient.full_name} registered successfully!')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'patient': {
                        'id': patient.id,
                        'name': patient.full_name,
                        'age': patient.age,
                        'gender': patient.gender
                    }
                })
            else:
                return redirect('health_assistant:landing')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Please correct the errors below.',
                    'errors': form.errors
                })
    else:
        form = PatientRegistrationForm()
    
    return render(request, 'health_assistant/patient_register.html', {'form': form})


@login_required
def screening_session(request):
    """Handle screening session creation"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        messages.error(request, 'Access denied. Health assistant role required.')
        return redirect('login')
    
    return render(request, 'health_assistant/screening_session.html')


@login_required
def my_sessions(request):
    """Display health assistant's screening sessions"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        messages.error(request, 'Access denied. Health assistant role required.')
        return redirect('login')
    
    sessions = ScreeningSession.objects.filter(
        created_by=request.user
    ).select_related('patient', 'screening_type').order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    
    # Filter by date range if provided
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        sessions = sessions.filter(created_at__date__gte=date_from)
    if date_to:
        sessions = sessions.filter(created_at__date__lte=date_to)
    
    return render(request, 'health_assistant/my_sessions.html', {
        'sessions': sessions,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to
    })


# API Endpoints
@login_required
def api_today_stats(request):
    """API endpoint to get today's statistics for health assistant"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    user = request.user
    today = timezone.now().date()
    
    # Get today's sessions
    todays_sessions = ScreeningSession.objects.filter(
        created_by=user,
        created_at__date=today
    )
    
    stats = {
        'todays_sessions': todays_sessions.count(),
        'completed_sessions': todays_sessions.filter(status='completed').count(),
        'pending_sessions': todays_sessions.filter(status='in_progress').count(),
        'total_patients': Patient.objects.filter(
            screening_sessions__created_by=user
        ).distinct().count()
    }
    
    return JsonResponse(stats)


@login_required
def api_recent_activity(request):
    """API endpoint to get recent activity for health assistant"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    user = request.user
    
    # Get recent sessions
    recent_sessions = ScreeningSession.objects.filter(
        created_by=user
    ).select_related('patient', 'screening_type').order_by('-created_at')[:5]
    
    activities = []
    for session in recent_sessions:
        activities.append({
            'title': f'Screening Session: {session.screening_type.name if session.screening_type else "Unknown"}',
            'description': f'Patient: {session.patient.full_name if session.patient else "Unknown"}',
            'time': format_time_diff(session.created_at)
        })
    
    return JsonResponse({'activities': activities})


@login_required
def api_search_patients(request):
    """API endpoint to search patients"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'patients': []})
    
    patients = Patient.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(phone_number__icontains=query)
    ).order_by('last_name', 'first_name')[:20]
    
    patient_data = []
    for patient in patients:
        patient_data.append({
            'id': patient.id,
            'name': f"{patient.first_name} {patient.last_name}",
            'age': patient.age,
            'gender': patient.gender,
            'phone': patient.phone_number
        })
    
    return JsonResponse({'patients': patient_data})


@login_required
def api_get_patient(request, patient_id):
    """API endpoint to get patient details"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        patient = Patient.objects.get(id=patient_id)
        return JsonResponse({
            'patient': {
                'id': patient.id,
                'name': f"{patient.first_name} {patient.last_name}",
                'age': patient.age,
                'gender': patient.gender,
                'phone': patient.phone_number,
                'email': patient.email,
                'address': patient.address
            }
        })
    except Patient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)


@login_required
def api_get_screening_types(request):
    """API endpoint to get available screening types"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    screening_types = ScreeningType.objects.filter(is_active=True)
    
    screening_type_data = []
    for screening_type in screening_types:
        screening_type_data.append({
            'id': screening_type.id,
            'name': screening_type.name,
            'description': screening_type.description
        })
    
    return JsonResponse({'screening_types': screening_type_data})


@login_required
def api_get_screening_type(request, screening_type_id):
    """API endpoint to get screening type details"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        screening_type = ScreeningType.objects.get(id=screening_type_id)
        return JsonResponse({
            'screening_type': {
                'id': screening_type.id,
                'name': screening_type.name,
                'description': screening_type.description
            }
        })
    except ScreeningType.DoesNotExist:
        return JsonResponse({'error': 'Screening type not found'}, status=404)


@login_required
def api_get_devices(request):
    """API endpoint to get available devices"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    devices = Device.objects.filter(status=Device.STATUS_ACTIVE).order_by('name')
    
    device_data = []
    for device in devices:
        device_data.append({
            'id': device.id,
            'name': device.name,
            'model': device.model_number,
            'device_type': device.device_type,
            'is_connected': device.connection_status == Device.CONNECTION_CONNECTED
        })
    
    return JsonResponse({'devices': device_data})


@login_required
def api_get_device(request, device_id):
    """API endpoint to get device details"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        device = Device.objects.get(id=device_id, status=Device.STATUS_ACTIVE)
        return JsonResponse({
            'device': {
                'id': device.id,
                'name': device.name,
                'model': device.model_number,
                'device_type': device.device_type,
                'is_connected': device.connection_status == Device.CONNECTION_CONNECTED
            }
        })
    except Device.DoesNotExist:
        return JsonResponse({'error': 'Device not found'}, status=404)


@login_required
def api_create_session(request):
    """API endpoint to create screening session"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            patient_id = request.POST.get('patient_id')
            screening_type_id = request.POST.get('screening_type_id')
            device_id = request.POST.get('device_id')
            
            # Validate inputs
            if not all([patient_id, screening_type_id, device_id]):
                return JsonResponse({'error': 'Missing required fields'}, status=400)
            
            # Get objects
            patient = get_object_or_404(Patient, id=patient_id)
            screening_type = get_object_or_404(ScreeningType, id=screening_type_id)
            device = get_object_or_404(Device, id=device_id, status=Device.STATUS_ACTIVE)
            
            # Check device availability
            if device.connection_status != Device.CONNECTION_CONNECTED or device.is_busy:
                return JsonResponse({'error': 'Device is not connected'}, status=400)
            
            # Create session
            session = ScreeningSession.objects.create(
                patient=patient,
                screening_type=screening_type,
                device=device,
                created_by=request.user,
                status='in_progress'
            )
            
            return JsonResponse({
                'success': True,
                'session_id': session.id,
                'message': 'Screening session created successfully'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def api_get_questionnaires(request):
    """API endpoint to get available questionnaires"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        # Optimize with annotate to get question count in a single query
        from django.db.models import Count
        
        questionnaires = Questionnaire.objects.filter(is_active=True).annotate(
            question_count=Count('questions')
        ).order_by('title')
        
        questionnaire_list = []
        
        for questionnaire in questionnaires:
            questionnaire_list.append({
                'id': questionnaire.id,
                'title': questionnaire.title,
                'description': questionnaire.description,
                'question_count': questionnaire.question_count  # Now from annotation
            })
        
        return JsonResponse({
            'success': True,
            'questionnaires': questionnaire_list
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def api_get_questionnaire(request, questionnaire_id):
    """API endpoint to get questionnaire details with questions"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        # Optimize with prefetch_related to avoid N+1 queries on options
        questionnaire = get_object_or_404(
            Questionnaire.objects.prefetch_related('questions__options'), 
            id=questionnaire_id, 
            is_active=True
        )
        
        questions_data = []
        for question in questionnaire.questions.order_by('order'):
            question_data = {
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'is_required': question.is_required,
                'options': []
            }
            
            # Add options for multiple choice questions (now cached due to prefetch_related)
            if question.question_type == question.TYPE_MULTIPLE_CHOICE:
                for option in question.options.order_by('order'):
                    question_data['options'].append({
                        'id': option.id,
                        'text': option.text
                    })
            
            questions_data.append(question_data)
        
        return JsonResponse({
            'success': True,
            'questionnaire': {
                'id': questionnaire.id,
                'title': questionnaire.title,
                'description': questionnaire.description,
                'questions': questions_data
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def api_submit_questionnaire(request):
    """API endpoint to submit questionnaire responses"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        # Get form data
        questionnaire_id = request.POST.get('questionnaire_id')
        patient_id = request.POST.get('patient_id')
        
        if not questionnaire_id or not patient_id:
            return JsonResponse({'success': False, 'message': 'Missing required data'}, status=400)
        
        # Get questionnaire and patient
        questionnaire = get_object_or_404(Questionnaire, id=questionnaire_id, is_active=True)
        patient = get_object_or_404(Patient, id=patient_id)
        
        # Import here to avoid circular imports
        from questionnaires.models import Response, Answer
        
        # Create response
        response = Response.objects.create(
            questionnaire=questionnaire,
            patient=patient,
            respondent=request.user,
            is_complete=True,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        # Process answers
        questions = questionnaire.questions.order_by('order')
        for question in questions:
            field_name = f'question_{question.id}'
            answer_value = request.POST.get(field_name)
            
            if answer_value:
                # Create answer
                answer = Answer.objects.create(
                    response=response,
                    question=question,
                    text_answer=''
                )
                
                # Save answer based on question type
                if question.question_type == question.TYPE_MULTIPLE_CHOICE:
                    # For multiple choice, save the option
                    try:
                        option = question.options.get(id=answer_value)
                        answer.option_answer.add(option)
                    except:
                        answer.text_answer = str(answer_value)
                else:
                    # For other types, save as text
                    answer.text_answer = str(answer_value)
                
                answer.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Questionnaire submitted successfully!',
            'response_id': response.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def api_export_questionnaire_data(request):
    """API endpoint to export questionnaire data"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        patient_id = request.GET.get('patient_id')
        questionnaire_id = request.GET.get('questionnaire_id')
        
        if not patient_id or not questionnaire_id:
            return JsonResponse({'success': False, 'message': 'Missing required parameters'}, status=400)
        
        # Get objects
        patient = get_object_or_404(Patient, id=patient_id)
        questionnaire = get_object_or_404(Questionnaire, id=questionnaire_id, is_active=True)
        
        # Import here to avoid circular imports
        from questionnaires.models import Response, Answer
        
        # Get responses
        responses = Response.objects.filter(
            patient=patient,
            questionnaire=questionnaire
        ).order_by('-created_at')
        
        export_data = []
        for response in responses:
            response_data = {
                'patient_id': patient.patient_id,
                'patient_name': patient.name,
                'questionnaire_title': questionnaire.title,
                'created_at': response.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if response.submitted_at else response.started_at.strftime('%Y-%m-%d %H:%M:%S'),
                'answers': []
            }
            
            # Get answers for this response
            answers = Answer.objects.filter(response=response).order_by('question__order')
            for answer in answers:
                answer_text = answer.text_answer
                if answer.option_answer.exists():
                    # If there are option answers, use the option text
                    option = answer.option_answer.first()
                    answer_text = option.text if option else answer_text
                
                response_data['answers'].append({
                    'question_text': answer.question.question_text,
                    'answer_text': answer_text
                })
            
            export_data.append(response_data)
        
        return JsonResponse({
            'success': True,
            'responses': export_data
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

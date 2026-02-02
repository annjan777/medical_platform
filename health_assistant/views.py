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
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
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
        return JsonResponse({'error': str(e)}, status=500)

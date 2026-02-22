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
from patients.models import Patient, PatientVitals
from screening.models import ScreeningSession, ScreeningType
from devices.models import Device
from questionnaires.models import Questionnaire, Question
from .forms import PatientRegistrationForm, VitalsForm


def has_patient_access(user):
    """Check if user has access to patient management"""
    allowed_roles = [User.Role.HEALTH_ASSISTANT, User.Role.SUPER_ADMIN, User.Role.DOCTOR]
    return user.role in allowed_roles


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
        # Check for phone number duplicates BEFORE validating the form
        phone_number = request.POST.get('phone_number')
        if phone_number:
            # Clean phone number for better matching
            cleaned_phone = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            existing_patients = Patient.objects.filter(
                Q(phone_number__icontains=cleaned_phone) | Q(phone_number__icontains=phone_number)
            )
            
            if existing_patients.exists():
                patient_list = []
                for p in existing_patients:
                    patient_list.append({
                        'id': p.id,
                        'patient_id': p.patient_id,
                        'first_name': p.first_name,
                        'last_name': p.last_name,
                        'name': f"{p.first_name} {p.last_name}",
                        'full_name': f"{p.first_name} {p.last_name}",
                        'age': p.age,
                        'gender': p.get_gender_display(),
                        'phone': p.phone_number,
                        'phone_number': p.phone_number,
                        'created_at': p.created_at.strftime('%Y-%m-%d %H:%M')
                    })
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'has_phone_duplicates': True,
                        'patients': patient_list,
                        'message': f'Patient with phone number {phone_number} already exists.',
                        'errors': {'phone_number': 'This phone number is already registered.'}
                    })
                else:
                    messages.error(request, f'Patient with phone number {phone_number} already exists.')
                    return redirect('health_assistant:landing')

        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            
            patient = form.save()
            print(f"DEBUG: Patient saved with ID: {patient.id}")
            print(f"DEBUG: Patient patient_id: {patient.patient_id}")
            print(f"DEBUG: Patient first_name: {patient.first_name}")
            print(f"DEBUG: Patient last_name: {patient.last_name}")
            
            messages.success(request, f'Patient {patient.full_name} registered successfully!')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data = {
                    'success': True,
                    'patient': {
                        'id': patient.id,
                        'patient_id': patient.patient_id,
                        'first_name': patient.first_name,
                        'last_name': patient.last_name,
                        'name': f"{patient.first_name} {patient.last_name}",
                        'full_name': f"{patient.first_name} {patient.last_name}",
                        'date_of_birth': patient.date_of_birth,
                        'age': patient.age,
                        'gender': patient.gender,
                        'phone': patient.phone_number,
                        'phone_number': patient.phone_number
                    }
                }
                print(f"DEBUG: Response data: {response_data}")
                return JsonResponse(response_data)
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
def screening_session(request, patient_id=None):
    """Handle screening session creation"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        messages.error(request, 'Access denied. Health assistant role required.')
        return redirect('login')
    
    # If patient_id is provided, pre-select the patient
    selected_patient = None
    if patient_id:
        try:
            selected_patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            messages.error(request, 'Patient not found.')
            return redirect('health_assistant:patient_list')
    
    return render(request, 'health_assistant/screening_session.html', {
        'selected_patient': selected_patient
    })


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
    """API endpoint to search patients with pagination and filtering"""
    if not has_patient_access(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    query = request.GET.get('q', '').strip()
    gender = request.GET.get('gender', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    page = int(request.GET.get('page', 1))
    export_format = request.GET.get('export', '')
    
    # Handle CSV export
    if export_format == 'csv':
        return export_patients_csv(query, gender, date_from, date_to)
    
    # Build filter conditions
    filters = Q()
    if query:
        # Check if query is a phone number (more flexible detection)
        cleaned_query = query.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        is_phone_query = cleaned_query.isdigit() and len(cleaned_query) >= 10
        
        if is_phone_query:
            # Search for exact phone number match first
            existing_patients = Patient.objects.filter(
                Q(phone_number__icontains=cleaned_query)
            ).order_by('created_at')[:20]
            
            # If exact phone match found, check for duplicates
            if existing_patients.count() > 0:
                patient_data = []
                for patient in existing_patients:
                    patient_data.append({
                        'id': patient.id,
                        'patient_id': patient.patient_id,
                        'first_name': patient.first_name,
                        'last_name': patient.last_name,
                        'name': f"{patient.first_name} {patient.last_name}",
                        'full_name': f"{patient.first_name} {patient.last_name}",
                        'age': patient.age if patient.age is not None else 0,
                        'gender': patient.gender,
                        'gender_display': patient.get_gender_display(),
                        'phone': patient.phone_number,
                        'phone_number': patient.phone_number,
                        'email': patient.email,
                        'city': patient.city,
                        'address': patient.address,
                        'created_at': patient.created_at.isoformat(),
                        'is_duplicate_phone': True
                    })
                
                return JsonResponse({
                    'patients': patient_data,
                    'has_phone_duplicates': True,
                    'message': f'Phone number {query} already exists. Please select existing patient or use different number.'
                })
        
        # Regular search by name or partial phone
        filters |= Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(patient_id__icontains=query) | Q(phone_number__icontains=query)
    
    print(f"DEBUG: Search query: '{query}'")
    print(f"DEBUG: Filters: {filters}")
    
    if gender:
        filters &= Q(gender=gender)
    if date_from:
        filters &= Q(created_at__date__gte=date_from)
    if date_to:
        filters &= Q(created_at__date__lte=date_to)
    
    # Get patients with pagination - if no query, return all patients
    if not query:
        patients = Patient.objects.all()
    else:
        patients = Patient.objects.filter(filters).order_by('-created_at')
    
    print(f"DEBUG: Found {patients.count()} patients")
    
    # Pagination
    from django.core.paginator import Paginator
    per_page = 20
    paginator = Paginator(patients, per_page)
    page_obj = paginator.get_page(page)
    
    patient_data = []
    for i, patient in enumerate(page_obj):
        print(f"DEBUG: Patient {i}: {patient.first_name} {patient.last_name} (ID: {patient.patient_id})")
        patient_data.append({
            'id': patient.id,
            'patient_id': patient.patient_id,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'name': f"{patient.first_name} {patient.last_name}",
            'full_name': f"{patient.first_name} {patient.last_name}",
            'age': patient.age if patient.age is not None else 0,
            'gender': patient.gender,
            'gender_display': patient.get_gender_display(),
            'phone': patient.phone_number,
            'phone_number': patient.phone_number,
            'email': patient.email,
            'city': patient.city,
            'address': patient.address,
            'created_at': patient.created_at.isoformat()
        })
    
    return JsonResponse({
        'patients': patient_data,
        'total_count': paginator.count,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        }
    })


@login_required
def api_get_patient(request, patient_id):
    """API endpoint to get patient details"""
    if not has_patient_access(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        patient = Patient.objects.get(id=patient_id)
        return JsonResponse({
            'patient': {
                'id': patient.id,
                'patient_id': patient.patient_id,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'name': f"{patient.first_name} {patient.last_name}",
                'full_name': f"{patient.first_name} {patient.last_name}",
                'age': patient.age,
                'gender': patient.gender,
                'gender_display': patient.get_gender_display(),
                'phone': patient.phone_number,
                'phone_number': patient.phone_number,
                'email': patient.email,
                'city': patient.city,
                'address': patient.address,
                'date_of_birth': patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else '',
                'created_at': patient.created_at.isoformat()
            }
        })
    except Patient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)


@login_required
def api_patient_update(request, patient_id):
    """API endpoint to update patient"""
    if not has_patient_access(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        patient = Patient.objects.get(id=patient_id)
        
        # Update fields
        patient.first_name = request.POST.get('first_name', patient.first_name)
        patient.last_name = request.POST.get('last_name', patient.last_name)
        
        date_of_birth = request.POST.get('date_of_birth')
        if date_of_birth:
            from datetime import datetime
            patient.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        
        patient.gender = request.POST.get('gender', patient.gender)
        patient.phone_number = request.POST.get('phone_number', patient.phone_number)
        patient.email = request.POST.get('email', patient.email)
        patient.city = request.POST.get('city', patient.city)
        patient.address = request.POST.get('address', patient.address)
        
        patient.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Patient updated successfully',
            'patient': {
                'id': patient.id,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'phone_number': patient.phone_number
            }
        })
        
    except Patient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def export_patients_csv(query, gender, date_from, date_to):
    """Export patients to CSV"""
    import csv
    from django.http import HttpResponse
    
    # Build filter conditions
    filters = Q()
    if query:
        filters |= Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(patient_id__icontains=query) | Q(phone_number__icontains=query)
    if gender:
        filters &= Q(gender=gender)
    if date_from:
        filters &= Q(created_at__date__gte=date_from)
    if date_to:
        filters &= Q(created_at__date__lte=date_to)
    
    patients = Patient.objects.filter(filters).order_by('-created_at')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="patients_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Patient ID', 'First Name', 'Last Name', 'Age', 'Gender', 'Phone', 'Email', 'City', 'Address', 'Created'])
    
    for patient in patients:
        writer.writerow([
            patient.patient_id,
            patient.first_name,
            patient.last_name,
            patient.age,
            patient.get_gender_display(),
            patient.phone_number,
            patient.email or '',
            patient.city or '',
            patient.address or '',
            patient.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    return response


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
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def api_submit_questionnaire(request):
    """Simple API endpoint to submit questionnaire responses"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get required data
        questionnaire_id = request.POST.get('questionnaire_id')
        patient_id = request.POST.get('patient_id')
        
        if not questionnaire_id or not patient_id:
            return JsonResponse({'success': False, 'message': 'Missing questionnaire ID or patient ID'}, status=400)
        
        # Get objects
        questionnaire = get_object_or_404(Questionnaire, id=questionnaire_id, is_active=True)
        
        # Try to get patient by patient_id (string) first, then by id (integer)
        try:
            patient = Patient.objects.get(patient_id=patient_id)
        except Patient.DoesNotExist:
            try:
                patient = Patient.objects.get(id=int(patient_id))
            except (Patient.DoesNotExist, ValueError):
                return JsonResponse({'success': False, 'message': 'Patient not found'}, status=404)
        
        # Import questionnaire models
        from questionnaires.models import Response, Answer
        
        # Create response
        response = Response.objects.create(
            questionnaire=questionnaire,
            patient=patient,
            respondent=request.user,
            is_complete=True,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        # Process all form data
        answer_count = 0
        
        for key, value in request.POST.items():
            if key.startswith('question_'):
                try:
                    question_id = key.split('_')[1]
                    question = questionnaire.questions.get(id=question_id)
                    
                    if question.question_type == question.TYPE_ATTACHMENT:
                        continue
                    
                    # Create answer
                    answer = Answer.objects.create(
                        response=response,
                        question=question,
                        text_answer=''
                    )
                    
                    # Handle different question types
                    if question.question_type == question.TYPE_MULTIPLE_CHOICE:
                        # For choice questions, value is option ID
                        if isinstance(value, list):
                            # Multiple choice
                            for option_id in value:
                                try:
                                    option = question.options.get(id=option_id)
                                    answer.option_answer.add(option)
                                except:
                                    answer.text_answer = str(option_id)
                        else:
                            # Single choice
                            try:
                                option = question.options.get(id=value)
                                answer.option_answer.add(option)
                            except:
                                answer.text_answer = str(value)
                    else:
                        # For text answers
                        answer.text_answer = str(value)
                    
                    answer.save()
                    answer_count += 1
                    
                except (ValueError, Question.DoesNotExist) as e:
                    continue  # Skip invalid question data
        
        # Now process FILES data (for attachment questions)
        for key, uploaded_file in request.FILES.items():
            if key.startswith('attachment_'):
                try:
                    question_id = key.split('_')[1]
                    question = questionnaire.questions.get(id=question_id)
                    
                    # Create answer for attachment
                    answer = Answer.objects.create(
                        response=response,
                        question=question,
                        file_answer=uploaded_file
                    )
                    
                    answer_count += 1
                    
                except (ValueError, Question.DoesNotExist) as e:
                    continue
        
        return JsonResponse({
            'success': True,
            'message': f'Questionnaire submitted successfully! {answer_count} answers saved.',
            'response_id': response.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def api_save_vitals(request):
    """API endpoint to save patient vitals"""
    if not has_patient_access(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        patient_id = request.POST.get('patient_id')
        if not patient_id:
            return JsonResponse({'success': False, 'message': 'Patient ID is required'}, status=400)
        
        # Try to get patient
        try:
            patient = Patient.objects.get(id=patient_id)
        except (Patient.DoesNotExist, ValueError):
            try:
                patient = Patient.objects.get(patient_id=patient_id)
            except Patient.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Patient not found'}, status=404)
        
        form = VitalsForm(request.POST)
        if form.is_valid():
            vitals = form.save(commit=False)
            vitals.patient = patient
            vitals.recorded_by = request.user
            vitals.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Vitals saved successfully',
                'vitals_id': vitals.id
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid data',
                'errors': form.errors
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def api_test_auth(request):
    """Test endpoint to check authentication"""
    return JsonResponse({
        'user': request.user.email,
        'role': request.user.role,
        'authenticated': request.user.is_authenticated,
        'session_key': request.session.session_key
    })


@login_required
def patient_list(request):
    """Patient management page for health assistants"""
    if not has_patient_access(request.user):
        messages.error(request, 'Access denied. Health assistant role required.')
        return redirect('login')
    
    return render(request, 'health_assistant/patient_list.html')
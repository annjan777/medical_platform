from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import Http404, HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
import json
import mimetypes
from urllib.parse import urlencode
from django.utils.dateformat import DateFormat
import re
import zipfile

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from accounts.models import User
from patients.models import Patient, PatientVitals
from screening.models import ScreeningAttachment, ScreeningSession, ScreeningType
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
            created_at__date=today
        )
        
        context['todays_sessions'] = todays_sessions.count()
        context['completed_sessions'] = todays_sessions.filter(status='completed').count()
        context['pending_sessions'] = todays_sessions.filter(status='in_progress').count()
        
        # Total patients in the system
        context['total_patients'] = Patient.objects.count()
        
        # Recent sessions
        context['recent_sessions'] = ScreeningSession.objects.select_related(
            'patient', 'screening_type'
        ).order_by('-created_at')[:10]
        
        # Device status (Only show available devices, or ones already assigned to this HA)
        context['devices'] = Device.objects.filter(
            Q(assigned_to__isnull=True) | Q(assigned_to=user),
            status=Device.STATUS_ACTIVE
        ).order_by('name')
        
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
            # Clean phone number for better matching (10 digits)
            cleaned_phone = re.sub(r'\D', '', phone_number)
            
            # Only check for duplicates if we have a valid-looking 10-digit number
            # Otherwise, the form validation will handle the error message
            if len(cleaned_phone) == 10:
                existing_patients = Patient.objects.filter(
                    Q(phone_number__icontains=cleaned_phone)
                )
            else:
                existing_patients = Patient.objects.none()
            
            if existing_patients.exists():
                patient_list = []
                for p in existing_patients:
                    patient_list.append({
                        'id': p.id,
                        'setu_id': p.setu_id,
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
            
            # Auto-create empty screening session to simplify workflow
            from screening.models import ScreeningType, ScreeningSession
            from django.utils import timezone
            
            default_type = ScreeningType.objects.first()
            if not default_type:
                default_type = ScreeningType.objects.create(
                    name="General Initial Screening",
                    code="general-initial-screening",
                    description="Auto-generated default screening type for registration workflow."
                )
                
            session, created = ScreeningSession.objects.get_or_create(
                id=patient.patient_id,
                defaults={
                    'patient': patient,
                    'screening_type': default_type,
                    'status': ScreeningSession.STATUS_IN_PROGRESS,
                    'scheduled_date': timezone.now(),
                    'created_by': request.user,
                    'consent_obtained': True,
                    'consented_at': timezone.now()
                }
            )
            
            # If the session was auto-created by the patient signal, update it.
            if not created and not session.created_by:
                session.created_by = request.user
                session.status = ScreeningSession.STATUS_IN_PROGRESS
                session.consent_obtained = True
                session.consented_at = timezone.now()
                session.save()
            
            messages.success(request, f'Patient {patient.full_name} registered successfully!')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data = {
                    'success': True,
                    'patient': {
                        'id': patient.id,
                        'setu_id': patient.setu_id,
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
                    'message': 'Please correct the highlighted errors.',
                    'errors': form.errors
                })
    else:
        form = PatientRegistrationForm()
    
    return render(request, 'health_assistant/patient_register.html', {'form': form})


@login_required
def screening_session(request, patient_id=None):
    """Handle screening session creation (Redirect to new automated workflow)"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        messages.error(request, 'Access denied. Health assistant role required.')
        return redirect('login')
    
    # In the simplified workflow, we no longer use manual device selection. 
    # All sessions are automatically created during patient registration/selection.
    return redirect('health_assistant:landing')


@login_required
def my_sessions(request):
    """Display health assistant's screening sessions"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        messages.error(request, 'Access denied. Health assistant role required.')
        return redirect('login')
    
    sessions = ScreeningSession.objects.select_related(
        'patient', 'screening_type'
    ).order_by('-created_at')
    
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
    
    # Pagination
    paginator = Paginator(sessions, 10) # 10 sessions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Preserve filters in pagination links while excluding duplicate 'page' arguments
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = query_params.urlencode()
    
    return render(request, 'health_assistant/my_sessions.html', {
        'sessions': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'query_string': query_string
    })

@login_required
def session_detail(request, session_id):
    """View and conduct an active screening session with IoT device integration."""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        messages.error(request, 'Access denied. Health assistant role required.')
        return redirect('login')
    
    session = get_object_or_404(ScreeningSession, id=session_id)
    devices = Device.objects.filter(status=Device.STATUS_ACTIVE)

    return render(request, 'health_assistant/session_conduct.html', {
        'session': session,
        'devices': devices,
    })


@login_required
def session_overview(request, session_id):
    """View a completed screening session overview specifically for Health Assistants."""
    if request.user.role not in [User.Role.HEALTH_ASSISTANT, User.Role.DOCTOR]:
        messages.error(request, 'Access denied. Health assistant or Doctor role required.')
        return redirect('login')
    
    session = get_object_or_404(ScreeningSession, id=session_id)
    
    # Fetch readings associated with this session from the reading_data JSON field
    from devices.models import DeviceReading
    readings = DeviceReading.objects.filter(
        patient=session.patient,
        # We also filter by time range to be safe, or just by the session_id string in JSON
        reading_data__session_id=str(session_id)
    ).order_by('recorded_at')

    # If not found by string, try int (since old sessions were integers)
    if not readings.exists() and str(session_id).isdigit():
        try:
            readings = DeviceReading.objects.filter(
                patient=session.patient,
                reading_data__session_id=int(session_id)
            ).order_by('recorded_at')
        except (ValueError, TypeError):
            pass
    
    base_template = 'doctor/base.html' if request.user.role == User.Role.DOCTOR else 'health_assistant/base_clean.html'
    back_url = 'doctor:patient_list' if request.user.role == User.Role.DOCTOR else 'health_assistant:my_sessions'
    
    return render(request, 'health_assistant/session_overview.html', {
        'session': session,
        'readings': readings,
        'base_template': base_template,
        'back_url': back_url
    })


def _user_can_view_session_file(user, session):
    if user.is_staff or getattr(user, 'is_super_admin', False):
        return True
    if user.role == User.Role.DOCTOR:
        return True
    if user.role == User.Role.HEALTH_ASSISTANT:
        return session.created_by_id == user.id
    return False


IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'}
TEXT_EXTENSIONS = {'txt', 'csv', 'json', 'xml', 'log', 'md', 'tsv'}


def _attachment_preview_context(attachment):
    file_name = attachment.file.name.rsplit('/', 1)[-1] if attachment.file else 'Attachment'
    file_name_lower = file_name.lower()
    guessed_type = mimetypes.guess_type(file_name)[0] or ''
    file_type = (attachment.file_type or guessed_type or '').lower()
    extension = file_name_lower.rsplit('.', 1)[-1] if '.' in file_name_lower else ''

    if file_type.startswith('image/') or extension in IMAGE_EXTENSIONS:
        preview_type = 'image'
        attachment_label = 'Image Scan'
    elif file_type.startswith('text/') or extension in TEXT_EXTENSIONS:
        preview_type = 'text'
        attachment_label = 'Text File'
    elif file_type == 'application/pdf' or extension == 'pdf':
        preview_type = 'pdf'
        attachment_label = 'PDF Document'
    elif file_type == 'application/zip' or extension == 'zip':
        preview_type = 'zip'
        attachment_label = 'Compressed ZIP Data'
    else:
        preview_type = 'unsupported'
        attachment_label = 'Data Attachment'

    return {
        'file_name': file_name,
        'file_type': file_type or 'Unknown file type',
        'preview_type': preview_type,
        'attachment_label': attachment_label,
    }


def _zip_entry_preview_type(entry_name):
    guessed_type = mimetypes.guess_type(entry_name)[0] or ''
    extension = entry_name.lower().rsplit('.', 1)[-1] if '.' in entry_name else ''

    if guessed_type.startswith('image/') or extension in IMAGE_EXTENSIONS:
        return 'image'
    if guessed_type.startswith('text/') or extension in TEXT_EXTENSIONS:
        return 'text'
    return 'unsupported'


def _format_file_size(size):
    if size < 1024:
        return f'{size} B'
    if size < 1024 * 1024:
        return f'{size / 1024:.1f} KB'
    return f'{size / (1024 * 1024):.1f} MB'


def _is_safe_zip_path(entry_name):
    entry_name = entry_name.replace('\\', '/')
    if not entry_name or entry_name.startswith('/') or ':' in entry_name:
        return False
    return all(part not in ('', '.', '..') for part in entry_name.split('/'))


def _normalize_zip_folder(folder_name):
    folder_name = folder_name.replace('\\', '/').strip('/')
    if not folder_name:
        return ''
    if not _is_safe_zip_path(folder_name):
        raise Http404('ZIP folder not found')
    return folder_name + '/'


def _zip_entry_url(session, attachment, entry_name, raw=False):
    query = {'path': entry_name}
    if raw:
        query['raw'] = '1'
    return '{}?{}'.format(
        reverse('health_assistant:session_zip_entry_view', kwargs={
            'session_id': session.id,
            'attachment_id': attachment.id,
        }),
        urlencode(query),
    )


def _zip_folder_url(session, attachment, folder_name):
    query = {}
    if folder_name:
        query['folder'] = folder_name.rstrip('/')
    url = reverse('health_assistant:session_attachment_view', kwargs={
        'session_id': session.id,
        'attachment_id': attachment.id,
    })
    if query:
        return '{}?{}'.format(url, urlencode(query))
    return url


def _zip_breadcrumbs(session, attachment, current_folder):
    breadcrumbs = [{
        'name': 'ZIP Root',
        'url': _zip_folder_url(session, attachment, ''),
        'active': current_folder == '',
    }]
    parts = [part for part in current_folder.strip('/').split('/') if part]
    for index, part in enumerate(parts):
        folder_path = '/'.join(parts[:index + 1]) + '/'
        breadcrumbs.append({
            'name': part,
            'url': _zip_folder_url(session, attachment, folder_path),
            'active': folder_path == current_folder,
        })
    return breadcrumbs


def _zip_parent_url(session, attachment, current_folder):
    parts = [part for part in current_folder.strip('/').split('/') if part]
    if not parts:
        return ''
    parent_folder = '/'.join(parts[:-1]) + '/' if len(parts) > 1 else ''
    return _zip_folder_url(session, attachment, parent_folder)


def _get_zip_folder_entries(session, attachment, current_folder):
    folders = {}
    rows = []

    try:
        attachment.file.open('rb')
        try:
            with zipfile.ZipFile(attachment.file) as archive:
                for info in sorted(archive.infolist(), key=lambda item: item.filename.lower()):
                    entry_name = info.filename.replace('\\', '/').strip('/')
                    if not _is_safe_zip_path(entry_name):
                        continue

                    entry_path = entry_name + '/' if info.is_dir() else entry_name
                    if current_folder and not entry_path.startswith(current_folder):
                        continue

                    remainder = entry_path[len(current_folder):] if current_folder else entry_path
                    remainder = remainder.strip('/')
                    if not remainder:
                        continue

                    parts = remainder.split('/')
                    if len(parts) > 1:
                        child_folder = current_folder + parts[0] + '/'
                        if child_folder not in folders:
                            folders[child_folder] = {
                                'kind': 'folder',
                                'name': parts[0],
                                'path': child_folder,
                                'size_label': 'Folder',
                                'preview_type': 'folder',
                                'preview_url': '',
                                'folder_url': _zip_folder_url(session, attachment, child_folder),
                            }
                        continue

                    if info.is_dir():
                        child_folder = current_folder + parts[0] + '/'
                        if child_folder not in folders:
                            folders[child_folder] = {
                                'kind': 'folder',
                                'name': parts[0],
                                'path': child_folder,
                                'size_label': 'Folder',
                                'preview_type': 'folder',
                                'preview_url': '',
                                'folder_url': _zip_folder_url(session, attachment, child_folder),
                            }
                        continue

                    preview_type = _zip_entry_preview_type(entry_name)
                    rows.append({
                        'kind': 'file',
                        'name': parts[0],
                        'path': entry_name,
                        'size_label': _format_file_size(info.file_size),
                        'preview_type': preview_type,
                        'preview_url': _zip_entry_url(session, attachment, entry_name) if preview_type in ('image', 'text') else '',
                        'folder_url': '',
                    })
        finally:
            attachment.file.close()
    except zipfile.BadZipFile:
        return [], 'This ZIP file could not be opened. Download it to inspect the original file.'
    except Exception:
        return [], 'This ZIP file could not be opened for inline browsing. Download it to inspect the original file.'

    combined_rows = list(folders.values()) + rows
    combined_rows.sort(key=lambda row: (1 if row['kind'] == 'file' else 0, row['name'].lower()))
    return combined_rows, ''


def _get_session_attachment_for_user(request, session_id, attachment_id):
    session = get_object_or_404(
        ScreeningSession.objects.select_related('patient', 'screening_type', 'created_by'),
        id=session_id,
    )
    attachment = get_object_or_404(ScreeningAttachment, id=attachment_id, session=session)

    if not _user_can_view_session_file(request.user, session):
        raise Http404('Attachment not found')

    return session, attachment


def _attachment_base_navigation(request, session):
    if request.user.role == User.Role.DOCTOR:
        return 'doctor/base.html', reverse('health_assistant:session_overview', kwargs={'session_id': session.id})
    if request.user.is_staff or getattr(request.user, 'is_super_admin', False):
        return 'health_assistant/base_clean.html', reverse('screening:session_detail', kwargs={'pk': session.id})
    return 'health_assistant/base_clean.html', reverse('health_assistant:session_overview', kwargs={'session_id': session.id})


@login_required
def session_attachment_view(request, session_id, attachment_id):
    """Preview a session attachment in a dedicated page."""
    if request.user.role not in [User.Role.HEALTH_ASSISTANT, User.Role.DOCTOR, User.Role.SUPER_ADMIN] and not request.user.is_staff:
        messages.error(request, 'Access denied. Authorized medical staff only.')
        return redirect('login')

    try:
        session, attachment = _get_session_attachment_for_user(request, session_id, attachment_id)
    except Http404:
        messages.error(request, 'You do not have permission to view this session attachment.')
        return redirect('health_assistant:my_sessions')

    preview_context = _attachment_preview_context(attachment)
    file_url = attachment.file.url if attachment.file else ''
    text_preview = ''
    text_preview_truncated = False
    text_preview_error = ''
    zip_entries = []
    zip_preview_error = ''
    zip_current_folder = ''
    zip_breadcrumbs = []
    zip_parent_url = ''

    if preview_context['preview_type'] == 'text' and attachment.file:
        preview_limit = 512 * 1024
        try:
            attachment.file.open('rb')
            try:
                raw_data = attachment.file.read(preview_limit + 1)
            finally:
                attachment.file.close()

            text_preview_truncated = len(raw_data) > preview_limit
            raw_data = raw_data[:preview_limit]
            try:
                text_preview = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                text_preview = raw_data.decode('latin-1', errors='replace')
        except Exception:
            text_preview_error = 'This text file could not be opened for inline preview. Download it to view the full file.'
    elif preview_context['preview_type'] == 'zip' and attachment.file:
        zip_current_folder = _normalize_zip_folder(request.GET.get('folder', ''))
        zip_entries, zip_preview_error = _get_zip_folder_entries(session, attachment, zip_current_folder)
        zip_breadcrumbs = _zip_breadcrumbs(session, attachment, zip_current_folder)
        zip_parent_url = _zip_parent_url(session, attachment, zip_current_folder)

    base_template, back_href = _attachment_base_navigation(request, session)

    return render(request, 'health_assistant/session_attachment_view.html', {
        'session': session,
        'attachment': attachment,
        'file_url': file_url,
        'download_label': 'Download ZIP' if preview_context['preview_type'] == 'zip' else 'Download Data',
        'text_preview': text_preview,
        'text_preview_truncated': text_preview_truncated,
        'text_preview_error': text_preview_error,
        'zip_entries': zip_entries,
        'zip_preview_error': zip_preview_error,
        'zip_current_folder': zip_current_folder,
        'zip_breadcrumbs': zip_breadcrumbs,
        'zip_parent_url': zip_parent_url,
        'is_zip_entry': False,
        'base_template': base_template,
        'back_href': back_href,
        **preview_context,
    })


@login_required
def session_zip_entry_view(request, session_id, attachment_id):
    """Preview or stream a supported file from inside a ZIP attachment."""
    if request.user.role not in [User.Role.HEALTH_ASSISTANT, User.Role.DOCTOR, User.Role.SUPER_ADMIN] and not request.user.is_staff:
        messages.error(request, 'Access denied. Authorized medical staff only.')
        return redirect('login')

    try:
        session, attachment = _get_session_attachment_for_user(request, session_id, attachment_id)
    except Http404:
        messages.error(request, 'You do not have permission to view this session attachment.')
        return redirect('health_assistant:my_sessions')

    entry_name = request.GET.get('path', '').replace('\\', '/').strip('/')
    if not _is_safe_zip_path(entry_name):
        raise Http404('ZIP entry not found')

    preview_type = _zip_entry_preview_type(entry_name)
    if preview_type not in ('image', 'text'):
        raise Http404('ZIP entry cannot be previewed')

    entry_basename = entry_name.rsplit('/', 1)[-1]
    content_type = mimetypes.guess_type(entry_name)[0] or 'application/octet-stream'
    raw_mode = request.GET.get('raw') == '1'
    raw_data = b''
    text_preview = ''
    text_preview_truncated = False
    text_preview_error = ''

    try:
        attachment.file.open('rb')
        try:
            with zipfile.ZipFile(attachment.file) as archive:
                try:
                    entry_info = archive.getinfo(entry_name)
                except KeyError as exc:
                    raise Http404('ZIP entry not found') from exc

                if entry_info.is_dir():
                    raise Http404('ZIP entry not found')

                if raw_mode:
                    raw_data = archive.read(entry_info)
                elif preview_type == 'text':
                    preview_limit = 512 * 1024
                    with archive.open(entry_info) as entry_file:
                        raw_text = entry_file.read(preview_limit + 1)
                    text_preview_truncated = len(raw_text) > preview_limit
                    raw_text = raw_text[:preview_limit]
                    try:
                        text_preview = raw_text.decode('utf-8')
                    except UnicodeDecodeError:
                        text_preview = raw_text.decode('latin-1', errors='replace')
        finally:
            attachment.file.close()
    except Http404:
        raise
    except zipfile.BadZipFile:
        raise Http404('ZIP file could not be opened')
    except Exception:
        if raw_mode:
            raise Http404('ZIP entry could not be opened')
        text_preview_error = 'This file could not be opened for inline preview. Download the ZIP to inspect it.'

    if raw_mode:
        response = HttpResponse(raw_data, content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{entry_basename}"'
        return response

    base_template, _session_back_href = _attachment_base_navigation(request, session)
    zip_back_href = reverse('health_assistant:session_attachment_view', kwargs={
        'session_id': session.id,
        'attachment_id': attachment.id,
    })
    raw_file_url = _zip_entry_url(session, attachment, entry_name, raw=True) if preview_type == 'image' else ''

    return render(request, 'health_assistant/session_attachment_view.html', {
        'session': session,
        'attachment': attachment,
        'file_url': raw_file_url,
        'download_label': 'Open File',
        'file_name': entry_basename,
        'file_type': content_type,
        'preview_type': preview_type,
        'attachment_label': 'Image Scan' if preview_type == 'image' else 'Text File',
        'text_preview': text_preview,
        'text_preview_truncated': text_preview_truncated,
        'text_preview_error': text_preview_error,
        'zip_entries': [],
        'zip_preview_error': '',
        'zip_current_folder': '',
        'zip_breadcrumbs': [],
        'zip_parent_url': '',
        'is_zip_entry': True,
        'base_template': base_template,
        'back_href': zip_back_href,
    })


@login_required
def api_associate_device(request, session_id):
    """API to associate or change the device for a session"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            device_id = request.POST.get('device_id')
            session = get_object_or_404(ScreeningSession, id=session_id)
            device = get_object_or_404(Device, id=device_id)
            
            session.device_used = device
            session.save()
            
            return JsonResponse({'success': True, 'message': f'Device {device.name} associated.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


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
        created_at__date=today
    )
    
    stats = {
        'todays_sessions': todays_sessions.count(),
        'completed_sessions': todays_sessions.filter(status='completed').count(),
        'pending_sessions': todays_sessions.filter(status='in_progress').count(),
        'total_patients': Patient.objects.count()
    }
    
    return JsonResponse(stats)


@login_required
def api_recent_activity(request):
    """API endpoint to get recent activity for health assistant"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    user = request.user
    
    # Get recent sessions
    recent_sessions = ScreeningSession.objects.select_related(
        'patient', 'screening_type'
    ).order_by('-created_at')[:5]
    
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
    
    try:
        query = request.GET.get('q', '').strip()
        gender = request.GET.get('gender', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        
        # Safely handle page parameter
        try:
            page_val = request.GET.get('page', 1)
            page = int(page_val) if page_val and str(page_val).isdigit() else 1
        except (ValueError, TypeError):
            page = 1
            
        export_format = request.GET.get('export', '')
        view_type = request.GET.get('view', '')
    
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
                            'setu_id': patient.setu_id,
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
            
            # Regular search by name, partial phone or Setu ID
            filters |= Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(patient_id__icontains=query) | Q(phone_number__icontains=query) | Q(setu_id__icontains=query)
        
        # print(f"DEBUG: Search query: '{query}'")
        # print(f"DEBUG: Filters: {filters}")
        
        if gender:
            filters &= Q(gender=gender)
        if date_from:
            filters &= Q(created_at__date__gte=date_from)
        if date_to:
            filters &= Q(created_at__date__lte=date_to)
            
        from django.db.models import Subquery, OuterRef
        from questionnaires.models import Response
        from patients.models import PatientNote
        
        if view_type == 'pending':
            filters &= Q(questionnaire_responses__isnull=False, questionnaire_responses__is_complete=True)
            filters &= ~Q(notes__note_type=PatientNote.NoteType.CONSULTATION, notes__is_important=False)
        elif view_type == 'completed':
            filters &= Q(questionnaire_responses__isnull=False, questionnaire_responses__is_complete=True)
            filters &= Q(notes__note_type=PatientNote.NoteType.CONSULTATION, notes__is_important=False)
        
        # Get patients with pagination
        # IMPORTANT: Apply filters to all cases, not just when query is present
        latest_response = Response.objects.filter(
            patient=OuterRef('pk'), 
            is_complete=True
        ).order_by('-submitted_at')
        
        patients = Patient.objects.filter(filters).annotate(
            latest_response_id=Subquery(latest_response.values('id')[:1])
        ).order_by('-created_at').distinct()
        
        # Pagination
        from django.core.paginator import Paginator
        per_page = 20
        paginator = Paginator(patients, per_page)
        page_obj = paginator.get_page(page)
        
        patient_data = []
        for i, patient in enumerate(page_obj):
            patient_data.append({
                'id': patient.id,
                'setu_id': patient.setu_id,
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
                'created_at': patient.created_at.isoformat() if patient.created_at else '',
                'latest_response_id': getattr(patient, 'latest_response_id', None)
            })
        
        return JsonResponse({
            'success': True,
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
    except Exception as e:
        import traceback
        error_msg = f"ERROR in api_search_patients: {str(e)}"
        print(error_msg)
        with open('/tmp/search_error.log', 'a') as f:
            f.write(f"\n--- {datetime.now()} ---\n")
            f.write(error_msg + "\n")
            f.write(traceback.format_exc() + "\n")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': f'Search failed: {str(e)}'
        }, status=200) # Use 200 to ensure JS handles the error message gracefully


@login_required
def api_get_patient(request, patient_id):
    """API endpoint to get patient details"""
    if not has_patient_access(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied'}, status=403)
    
    try:
        patient = Patient.objects.get(id=patient_id)
        
        # Auto-create empty screening session for this existing patient to simplify workflow
        from screening.models import ScreeningType, ScreeningSession
        from django.utils import timezone
        
        default_type = ScreeningType.objects.first()
        if not default_type:
            default_type = ScreeningType.objects.create(
                name="General Initial Screening",
                code="general-initial-screening",
                description="Auto-generated default screening type for workflow."
            )
            
        ScreeningSession.objects.get_or_create(
            id=patient.patient_id,
            defaults={
                'patient': patient,
                'screening_type': default_type,
                'status': ScreeningSession.STATUS_IN_PROGRESS,
                'scheduled_date': timezone.now(),
                'created_by': request.user,
                'consent_obtained': True,
                'consented_at': timezone.now()
            }
        )
        
        return JsonResponse({
            'success': True,
            'patient': {
                'id': patient.id,
                'setu_id': patient.setu_id,
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
                'date_of_birth': patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else '',
                'created_at': patient.created_at.isoformat() if patient.created_at else ''
            }
        })
    except Patient.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Patient not found',
            'message': 'The selected patient could not be found.'
        }, status=200)
    except Exception as e:
        import traceback
        print(f"ERROR in api_get_patient: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': f'Failed to retrieve patient details: {str(e)}'
        }, status=200)


@login_required
def api_patient_update(request, patient_id):
    """API endpoint to update patient"""
    if not has_patient_access(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        patient = Patient.objects.get(id=patient_id)
        
        # Handle JSON data if provided
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
        else:
            data = request.POST

        # Update fields
        patient.setu_id = data.get('setu_id', patient.setu_id)
        patient.first_name = data.get('first_name', patient.first_name)
        patient.last_name = data.get('last_name', patient.last_name)
        
        date_of_birth = data.get('date_of_birth')
        if date_of_birth:
            from datetime import datetime
            try:
                patient.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass
        
        patient.gender = data.get('gender', patient.gender)
        patient.phone_number = data.get('phone_number', patient.phone_number)
        patient.email = data.get('email', patient.email)
        patient.city = data.get('city', patient.city)
        patient.address = data.get('address', patient.address)
        
        patient.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Patient updated successfully',
            'patient': {
                'id': patient.id,
                'setu_id': patient.setu_id,
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
        filters |= Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(patient_id__icontains=query) | Q(phone_number__icontains=query) | Q(setu_id__icontains=query)
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
    writer.writerow(['Setu ID', 'Patient ID', 'First Name', 'Last Name', 'Age', 'Gender', 'Phone', 'Email', 'City', 'Address', 'Created'])
    
    for patient in patients:
        writer.writerow([
            patient.setu_id,
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
def api_get_products(request):
    """API endpoint to get available screening products (types)"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    screening_types = ScreeningType.objects.filter(is_active=True)
    
    product_data = []
    for st in screening_types:
        # Count available questionnaires
        q_count = 0
        if st.pre_screening_questionnaire: q_count += 1
        if st.post_screening_questionnaire: q_count += 1
        
        product_data.append({
            'id': st.id,
            'name': st.name,
            'description': st.description,
            'questionnaires_count': q_count
        })
    
    return JsonResponse({'products': product_data})


@login_required
def api_get_product(request, product_id):
    """API endpoint to get screening product details"""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        st = ScreeningType.objects.get(id=product_id)
        return JsonResponse({
            'product': {
                'id': st.id,
                'name': st.name,
                'description': st.description
            }
        })
    except ScreeningType.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


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
@require_POST
def api_reset_devices_disconnected(request):
    """Mark all active devices as disconnected before a ping cycle."""
    if request.user.role != User.Role.HEALTH_ASSISTANT:
        return JsonResponse({'error': 'Access denied'}, status=403)

    updated = Device.objects.filter(status=Device.STATUS_ACTIVE).update(
        connection_status=Device.CONNECTION_DISCONNECTED
    )
    return JsonResponse({'reset': updated})


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
            import json
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                patient_id = data.get('patient_id')
                screening_type_id = data.get('screening_type_id')
                device_id = data.get('device_id')
            else:
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
            
            from django.utils import timezone
            # Create or update session using patient_id as session ID
            session, created = ScreeningSession.objects.update_or_create(
                id=patient.patient_id,
                defaults={
                    'patient': patient,
                    'screening_type': screening_type,
                    'device_used': device,
                    'created_by': request.user,
                    'status': 'in_progress',
                    'scheduled_date': timezone.now(),
                    'consent_obtained': True,
                    'consented_at': timezone.now()
                }
            )
            
            return JsonResponse({
                'success': True,
                'session_id': session.id, # This is now the string patient_id
                'message': 'Screening session updated successfully' if not created else 'Screening session created successfully'
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
            submitted_at=timezone.now(),
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        # Link session and vitals if provided or available
        session_id = request.POST.get('session_id')
        vitals_id = request.POST.get('vitals_id')
        
        if session_id:
            try:
                session = ScreeningSession.objects.get(id=session_id)
                response.session = session
                if not vitals_id and session.vitals:
                    response.vitals = session.vitals
            except ScreeningSession.DoesNotExist:
                pass
                
        if vitals_id:
            try:
                vitals = PatientVitals.objects.get(id=vitals_id)
                response.vitals = vitals
            except PatientVitals.DoesNotExist:
                pass
        
        # Fallback to latest vitals recorded *before* submission if none specifically linked
        if not response.vitals:
            # Use the submission time for filtering
            check_time = response.submitted_at or timezone.now()
            response.vitals = PatientVitals.objects.filter(
                patient=patient, 
                recorded_at__lte=check_time
            ).order_by('-recorded_at').first()
            
            # If still none recorded before (backwards compatibility for rare edge cases), get very latest
            if not response.vitals:
                response.vitals = PatientVitals.objects.filter(patient=patient).order_by('-recorded_at').first()
            
        response.save()
        
        # Process all form data
        answer_count = 0
        
        for key in request.POST.keys():
            if key.startswith('question_'):
                try:
                    question_id = key.split('_')[1]
                    question = questionnaire.questions.get(id=question_id)
                    
                    if question.question_type == question.TYPE_ATTACHMENT:
                        continue
                        
                    value_list = request.POST.getlist(key)
                    if not value_list or (len(value_list) == 1 and not value_list[0]):
                        # Skip empty submissions unless required (handled elsewhere)
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
                        for val in value_list:
                            try:
                                option = question.options.get(id=val)
                                answer.option_answer.add(option)
                            except:
                                answer.text_answer = str(val)
                    else:
                        # For text answers, just use the first item
                        answer.text_answer = str(value_list[0])
                    
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
            
            # Link to session if provided
            session_id = request.POST.get('session_id')
            if session_id:
                try:
                    session = ScreeningSession.objects.get(id=session_id)
                    session.vitals = vitals
                    session.save()
                except ScreeningSession.DoesNotExist:
                    pass
            
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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib import messages
from django.db.models import Q, Subquery, OuterRef
from accounts.models import User
from patients.models import Patient
from questionnaires.models import Response, Questionnaire
from screening.models import ScreeningSession
from textwrap import dedent


class DoctorRequiredMixin(LoginRequiredMixin):
    """Mixin to ensure user is a Doctor"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != User.Role.DOCTOR:
            messages.error(request, 'Access denied. Dentist role required.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

class SessionListView(DoctorRequiredMixin, ListView):
    model = ScreeningSession
    template_name = 'doctor/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20

    def get_queryset(self):
        queryset = ScreeningSession.objects.select_related('patient', 'screening_type').order_by('-created_at')
        
        q = self.request.GET.get('q')
        status = self.request.GET.get('status')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if q:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=q) | 
                Q(patient__last_name__icontains=q) | 
                Q(patient__patient_id__icontains=q)
            )
        
        if status:
            queryset = queryset.filter(status=status)
            
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        context['query_string'] = query_params.urlencode()
        return context

@login_required
def doctor_home(request):
    """Doctor dashboard home page"""
    if request.user.role != User.Role.DOCTOR:
        messages.error(request, 'Access denied. Dentist role required.')
        return redirect('login')
    
    # Get statistics for the dashboard
    total_patients = Patient.objects.count()
    total_responses = Response.objects.count()
    recent_responses = Response.objects.select_related('patient', 'questionnaire').order_by('-submitted_at')[:10]
    
    context = {
        'total_patients': total_patients,
        'total_responses': total_responses,
        'recent_responses': recent_responses,
    }
    return render(request, 'doctor/home.html', context)

class PatientListView(DoctorRequiredMixin, ListView):
    model = Patient
    template_name = 'doctor/patient_management.html'
    context_object_name = 'patients'
    paginate_by = 20

    def get_queryset(self):
        queryset = Patient.objects.all().order_by('-created_at')
        q = self.request.GET.get('q')
        needs_follow_up = self.request.GET.get('needs_follow_up')
        
        if q:
            queryset = queryset.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(patient_id__icontains=q)
            )
            
        from patients.models import PatientNote
        latest_consultation = PatientNote.objects.filter(
            patient=OuterRef('pk'), 
            note_type=PatientNote.NoteType.CONSULTATION
        ).order_by('-created_at')
        
        queryset = queryset.annotate(
            latest_is_important=Subquery(latest_consultation.values('is_important')[:1])
        )
            
        if needs_follow_up == 'yes':
            queryset = queryset.filter(latest_is_important=True)
        elif needs_follow_up == 'no':
            queryset = queryset.filter(latest_is_important=False)
            
        return queryset

class PendingConsultationListView(PatientListView):
    def get_queryset(self):
        queryset = super().get_queryset()
        latest_response = Response.objects.filter(patient=OuterRef('pk'), is_complete=True).order_by('-submitted_at')
        return queryset.filter(questionnaire_responses__isnull=False, questionnaire_responses__is_complete=True)\
                       .exclude(notes__note_type='CONSULTATION', notes__is_important=False)\
                       .annotate(latest_response_id=Subquery(latest_response.values('id')[:1]))\
                       .distinct()
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Pending Consultations"
        context['page_subtitle'] = "Patients waiting for dentist's consultation or needing active follow-up."
        context['view'] = 'pending'
        return context

class CompletedConsultationListView(PatientListView):
    def get_queryset(self):
        queryset = super().get_queryset()
        latest_response = Response.objects.filter(patient=OuterRef('pk'), is_complete=True).order_by('-submitted_at')
        return queryset.filter(questionnaire_responses__isnull=False, questionnaire_responses__is_complete=True, notes__note_type='CONSULTATION', notes__is_important=False)\
                       .annotate(latest_response_id=Subquery(latest_response.values('id')[:1]))\
                       .distinct()
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Completed Consultations"
        context['page_subtitle'] = "Patients who have received a consultation."
        context['view'] = 'completed'
        return context

class PatientDetailView(DoctorRequiredMixin, DetailView):
    model = Patient
    template_name = 'doctor/patient_detail.html'
    context_object_name = 'patient'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the latest completed response for this patient
        context['latest_response'] = self.object.questionnaire_responses.filter(is_complete=True).order_by('-submitted_at').first()
        # Get the latest consultation note for this patient
        context['latest_consultation'] = self.object.notes.filter(note_type='CONSULTATION').order_by('-created_at').first()
        return context

class ResponseListView(DoctorRequiredMixin, ListView):
    model = Response
    template_name = 'doctor/response_management.html'
    context_object_name = 'responses'
    paginate_by = 20

    def get_queryset(self):
        queryset = Response.objects.select_related('patient', 'questionnaire', 'respondent')
        
        # Filter by questionnaire if specified
        questionnaire_id = self.request.GET.get('questionnaire')
        if questionnaire_id:
            queryset = queryset.filter(questionnaire_id=questionnaire_id)
            
        # Filter by patient if specified
        patient_id = self.request.GET.get('patient')
        if patient_id:
            queryset = queryset.filter(Q(patient__patient_id__icontains=patient_id) | 
                                     Q(patient__first_name__icontains=patient_id) | 
                                     Q(patient__last_name__icontains=patient_id))
            
        # Filter by date range if specified
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(started_at__date__gte=date_from_obj)
            except ValueError:
                pass
                
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(started_at__date__lte=date_to_obj)
            except ValueError:
                pass
            
        return queryset.order_by('-submitted_at', '-started_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questionnaires'] = Questionnaire.objects.filter(is_active=True)
        return context

class ConsultationNoteCreateMixin:
    """Handle consultation note submission from the editable response view."""

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        patient = self.object.patient

        # Gather data from the form
        provisional_diagnosis = request.POST.get('provisional_diagnosis', '').strip()
        on_examination = request.POST.get('on_examination', '').strip()
        investigations = request.POST.get('investigations', '').strip()
        advice = request.POST.get('advice', '').strip()
        further_followup = request.POST.get('further_followup') == 'on'

        # Gather prescriptions
        prescription_types = request.POST.getlist('pres_type[]')
        medicine_names = request.POST.getlist('pres_medicine[]')
        dosages = request.POST.getlist('pres_dosage[]')
        instructions = request.POST.getlist('pres_instructions[]')
        durations = request.POST.getlist('pres_duration[]')
        others = request.POST.getlist('pres_others[]')

        prescriptions_text = ""
        for i in range(len(medicine_names)):
            med = medicine_names[i].strip()
            if med:
                typ = prescription_types[i].strip() if i < len(prescription_types) else ""
                dos = dosages[i].strip() if i < len(dosages) else ""
                ins = instructions[i].strip() if i < len(instructions) else ""
                dur = durations[i].strip() if i < len(durations) else ""
                oth = others[i].strip() if i < len(others) else ""
                prescriptions_text += f"&bull; <em>{typ}</em>: <strong>{med}</strong> | {dos} | {dur} days | {ins} | {oth}<br>"

        # Build the final content
        content_lines = []
        if provisional_diagnosis:
            content_lines.append(f"<strong>Provisional Diagnosis</strong><br>{provisional_diagnosis}")
        if on_examination:
            content_lines.append(f"<strong>On Examination</strong><br>{on_examination}")
        if investigations:
            content_lines.append(f"<strong>Investigations</strong><br>{investigations}")
        if prescriptions_text:
            content_lines.append(f"<strong>Prescriptions</strong><br>{prescriptions_text}")
        if advice:
            content_lines.append(f"<strong>Advice</strong><br>{advice}")

        followup_text = "Yes" if further_followup else "No"
        content_lines.append(f"<strong>Further Followup Required</strong><br>{followup_text}")

        content = "<br><br>".join(content_lines)

        from patients.models import PatientNote
        PatientNote.objects.create(
            patient=patient,
            author=request.user,
            note_type=PatientNote.NoteType.CONSULTATION,
            title=f"Consultation Note - {self.object.questionnaire.title}",
            content=content,
            is_important=further_followup
        )

        messages.success(request, "Consultation note added successfully to patient's record.")
        return redirect('doctor:pending_consultations')


class ResponseDetailView(ConsultationNoteCreateMixin, DoctorRequiredMixin, DetailView):
    model = Response
    template_name = 'doctor/response_detail.html'
    context_object_name = 'response'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vitals'] = self.object.patient.vitals.order_by('-recorded_at').first()
        # Fetch previous consultations for this patient
        context['previous_consultations'] = self.object.patient.notes.filter(note_type='CONSULTATION').order_by('-created_at')
        return context

class ResponseReadOnlyView(DoctorRequiredMixin, DetailView):
    model = Response
    template_name = 'doctor/response_detail.html'
    context_object_name = 'response'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vitals'] = self.object.patient.vitals.order_by('-recorded_at').first()
        context['previous_consultations'] = self.object.patient.notes.filter(note_type='CONSULTATION').order_by('-created_at')
        context['read_only'] = True
        return context

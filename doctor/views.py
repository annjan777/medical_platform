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
        # Get prescriptions
        from patients.models import Document
        context['prescriptions'] = self.object.documents.filter(document_type=Document.DocumentType.PRESCRIPTION).order_by('-uploaded_at')
        return context

@login_required
def download_prescription(request, document_id):
    from patients.models import Document
    from doctor.pdf_utils import generate_presigned_url
    from django.http import Http404
    
    document = get_object_or_404(Document, id=document_id, document_type=Document.DocumentType.PRESCRIPTION)
    
    object_name = document.description
    if object_name and object_name.startswith('prescriptions/'):
        try:
            url = generate_presigned_url(object_name)
            return redirect(url)
        except Exception:
            pass
            
    if document.file:
        return redirect(document.file.url)
        
    raise Http404("Prescription file not found")

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

    ORAL_PATHOLOGY_CHOICES = (
        'Gingivitis',
        'Aphthous stomatitis',
        'Oral candidiasis',
        'Dental fluorosis',
    )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        patient = self.object.patient

        # Gather data from the form
        oral_pathologies = [
            pathology
            for pathology in request.POST.getlist('oral_pathologies[]')
            if pathology in self.ORAL_PATHOLOGY_CHOICES
        ]
        oral_pathologies_other = request.POST.get('oral_pathologies_other', '').strip()
        if oral_pathologies_other:
            oral_pathologies.append(oral_pathologies_other)
        provisional_diagnosis = request.POST.get('provisional_diagnosis', '').strip()
        on_examination = request.POST.get('on_examination', '').strip()
        white_patch = request.POST.get('white_patch', 'No').strip().capitalize()
        red_patch = request.POST.get('red_patch', 'No').strip().capitalize()
        investigations = request.POST.get('investigations', '').strip()
        advice = request.POST.get('advice', '').strip()
        further_followup = request.POST.get('further_followup') == 'on'
        specialist_referral = request.POST.get('specialist_referral') == 'on'

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
        if oral_pathologies:
            content_lines.append(f"<strong>Oral Pathologies</strong><br>{', '.join(oral_pathologies)}")
        if provisional_diagnosis:
            content_lines.append(f"<strong>Provisional Diagnosis</strong><br>{provisional_diagnosis}")
        if on_examination:
            content_lines.append(f"<strong>On Examination</strong><br>{on_examination}")
        if investigations:
            content_lines.append(f"<strong>Investigations</strong><br>{investigations}")
        content_lines.append(f"<strong>White patch present</strong><br>{white_patch}")
        content_lines.append(f"<strong>Red patch present</strong><br>{red_patch}")
        if prescriptions_text:
            content_lines.append(f"<strong>Prescriptions</strong><br>{prescriptions_text}")
        if advice:
            content_lines.append(f"<strong>Advice</strong><br>{advice}")

        followup_text = "Yes" if further_followup else "No"
        content_lines.append(f"<strong>Further Followup Required</strong><br>{followup_text}")

        referral_text = "Yes" if specialist_referral else "No"
        content_lines.append(f"<strong>Specialist Referral Required</strong><br>{referral_text}")

        content = "<br><br>".join(content_lines)

        from patients.models import PatientNote, Document, MedicalRecord
        
        # Save the consultation note
        PatientNote.objects.create(
            patient=patient,
            author=request.user,
            note_type=PatientNote.NoteType.CONSULTATION,
            title=f"Consultation Note - {self.object.questionnaire.title}",
            content=content,
            is_important=further_followup
        )

        # Generate Prescription PDF
        try:
            from doctor.pdf_utils import generate_prescription_pdf, upload_pdf_to_s3
            from django.utils import timezone
            from django.core.files.base import ContentFile
            
            # Prepare medicines list for PDF
            pdf_medicines = []
            for i in range(len(medicine_names)):
                med = medicine_names[i].strip()
                if med:
                    pdf_medicines.append({
                        'type': prescription_types[i].strip() if i < len(prescription_types) else "",
                        'name': med,
                        'dose': dosages[i].strip() if i < len(dosages) else "",
                        'instructions': instructions[i].strip() if i < len(instructions) else "",
                        'duration': durations[i].strip() if i < len(durations) else "",
                        'others': others[i].strip() if i < len(others) else ""
                    })

            # Fetch medical record for history
            medical_record = MedicalRecord.objects.filter(patient=patient).first()
            
            # Fetch vitals
            vitals = patient.vitals.order_by('-recorded_at').first()

            context = {
                'request': request,
                'patient': patient,
                'date': timezone.now().strftime("%d %b %Y, %I:%M %p"),
                'vitals': vitals,
                'medical_history': medical_record.chronic_conditions if medical_record else "None",
                'family_history': medical_record.family_history if medical_record else "None",
                'medications': medical_record.current_medications if medical_record else "None",
                'allergies': medical_record.allergies if medical_record else "None",
                'diagnosis': provisional_diagnosis,
                'white_patch': white_patch,
                'red_patch': red_patch,
                'medicines': pdf_medicines,
                'investigations': investigations,
                'advice': advice,
                'followup_required': "Yes" if further_followup else "No",
                'specialist_referral_required': "Yes" if specialist_referral else "No",
                'notes': on_examination,
                'assistant_name': (
                    self.object.respondent.get_full_name() or
                    self.object.respondent.email
                ) if self.object.respondent else "-",
                'doctor': request.user,
            }
            
            pdf_bytes = generate_prescription_pdf(context)
            
            # Try to upload to S3 if configured, otherwise save locally
            try:
                identifier = patient.setu_id if patient.setu_id else patient.patient_id
                object_name = upload_pdf_to_s3(pdf_bytes, identifier)
                
                Document.objects.create(
                    patient=patient,
                    uploaded_by=request.user,
                    document_type=Document.DocumentType.PRESCRIPTION,
                    title=f"Prescription - {timezone.now().strftime('%Y-%m-%d')}",
                    description=object_name,
                )
            except Exception as e:
                # Fallback to local storage if S3 fails or is not configured
                identifier = patient.setu_id if patient.setu_id else patient.patient_id
                doc = Document.objects.create(
                    patient=patient,
                    uploaded_by=request.user,
                    document_type=Document.DocumentType.PRESCRIPTION,
                    title=f"Prescription - {timezone.now().strftime('%Y-%m-%d')}",
                )
                doc.file.save(f"prescriptions/{identifier}.pdf", ContentFile(pdf_bytes))
                
        except Exception as e:
            # We don't want to break the whole flow if PDF generation fails
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to generate prescription PDF: {str(e)}")

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
        context['already_diagnosed'] = self.object.patient.notes.filter(note_type='CONSULTATION').exists()
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

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.http import FileResponse
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView, View
)
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from ..forms import MedicalRecordForm, VitalSignsForm, PatientNoteForm, DocumentForm
from ..models import Patient, MedicalRecord, VitalSigns, PatientNote, Document

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to ensure user is staff"""
    def test_func(self):
        return self.request.user.is_staff

class MedicalRecordUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    """View for updating a patient's medical record"""
    model = MedicalRecord
    form_class = MedicalRecordForm
    template_name = 'patients/medical_record_form.html'
    success_message = _('Medical record updated successfully')
    
    def get_object(self):
        patient = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])
        medical_record, created = MedicalRecord.objects.get_or_create(patient=patient)
        return medical_record
    
    def get_success_url(self):
        return reverse_lazy('patients:dashboard', kwargs={'pk': self.kwargs['patient_pk']})

class VitalSignsCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    """View for recording new vital signs"""
    model = VitalSigns
    form_class = VitalSignsForm
    template_name = 'patients/vital_signs_form.html'
    success_message = _('Vital signs recorded successfully')
    
    def get_initial(self):
        initial = super().get_initial()
        patient = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])
        initial['patient'] = patient
        return initial
    
    def form_valid(self, form):
        form.instance.patient_id = self.kwargs['patient_pk']
        form.instance.recorded_by = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('patients:dashboard', kwargs={'pk': self.kwargs['patient_pk']})

class VitalSignsUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    """View for updating existing vital signs"""
    model = VitalSigns
    form_class = VitalSignsForm
    template_name = 'patients/vital_signs_form.html'
    success_message = _('Vital signs updated successfully')
    
    def get_queryset(self):
        return VitalSigns.objects.filter(patient_id=self.kwargs['patient_pk'])
    
    def get_success_url(self):
        return reverse_lazy('patients:dashboard', kwargs={'pk': self.kwargs['patient_pk']})

class VitalSignsDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    """View for deleting vital signs"""
    model = VitalSigns
    template_name = 'patients/vital_signs_confirm_delete.html'
    success_message = _('Vital signs deleted successfully')
    
    def get_queryset(self):
        return VitalSigns.objects.filter(patient_id=self.kwargs['patient_pk'])
    
    def get_success_url(self):
        return reverse_lazy('patients:dashboard', kwargs={'pk': self.kwargs['patient_pk']})
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

class PatientNoteCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    """View for adding a new patient note"""
    model = PatientNote
    form_class = PatientNoteForm
    template_name = 'patients/patient_note_form.html'
    success_message = _('Note added successfully')
    
    def get_initial(self):
        initial = super().get_initial()
        patient = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])
        initial['patient'] = patient
        return initial
    
    def form_valid(self, form):
        form.instance.patient_id = self.kwargs['patient_pk']
        form.instance.author = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('patients:dashboard', kwargs={'pk': self.kwargs['patient_pk']})

class PatientNoteUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    """View for updating a patient note"""
    model = PatientNote
    form_class = PatientNoteForm
    template_name = 'patients/patient_note_form.html'
    success_message = _('Note updated successfully')
    
    def get_queryset(self):
        return PatientNote.objects.filter(patient_id=self.kwargs['patient_pk'])
    
    def get_success_url(self):
        return reverse_lazy('patients:dashboard', kwargs={'pk': self.kwargs['patient_pk']})

class PatientNoteDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    """View for deleting a patient note"""
    model = PatientNote
    template_name = 'patients/patient_note_confirm_delete.html'
    success_message = _('Note deleted successfully')
    
    def get_queryset(self):
        return PatientNote.objects.filter(patient_id=self.kwargs['patient_pk'])
    
    def get_success_url(self):
        return reverse_lazy('patients:dashboard', kwargs={'pk': self.kwargs['patient_pk']})
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

class DocumentUploadView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    """View for uploading a new document"""
    model = Document
    form_class = DocumentForm
    template_name = 'patients/document_upload.html'
    success_message = _('Document uploaded successfully')
    
    def get_initial(self):
        initial = super().get_initial()
        patient = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])
        initial['patient'] = patient
        return initial
    
    def form_valid(self, form):
        form.instance.patient_id = self.kwargs['patient_pk']
        form.instance.uploaded_by = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('patients:dashboard', kwargs={'pk': self.kwargs['patient_pk']})

class DocumentUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    """View for updating document metadata"""
    model = Document
    form_class = DocumentForm
    template_name = 'patients/document_upload.html'
    success_message = _('Document updated successfully')
    
    def get_queryset(self):
        return Document.objects.filter(patient_id=self.kwargs['patient_pk'])
    
    def get_success_url(self):
        return reverse_lazy('patients:dashboard', kwargs={'pk': self.kwargs['patient_pk']})

class DocumentDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    """View for deleting a document"""
    model = Document
    template_name = 'patients/document_confirm_delete.html'
    success_message = _('Document deleted successfully')
    
    def get_queryset(self):
        return Document.objects.filter(patient_id=self.kwargs['patient_pk'])
    
    def get_success_url(self):
        return reverse_lazy('patients:dashboard', kwargs={'pk': self.kwargs['patient_pk']})
    
    def delete(self, request, *args, **kwargs):
        document = self.get_object()
        # Delete the actual file from storage
        document.file.delete(save=False)
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

class DocumentDownloadView(StaffRequiredMixin, View):
    """View for downloading a document"""
    def get(self, request, *args, **kwargs):
        document = get_object_or_404(
            Document, 
            pk=kwargs['pk'], 
            patient_id=kwargs['patient_pk']
        )
        return redirect(document.file.url)

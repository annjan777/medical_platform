from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView, View
)
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from ..forms import PatientForm, PatientSearchForm
from ..models import Patient, MedicalRecord, VitalSigns, PatientNote, Document

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to ensure user is staff"""
    def test_func(self):
        return self.request.user.is_staff

class PatientListView(StaffRequiredMixin, ListView):
    """View for listing patients with search and filter functionality"""
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Patient.objects.all().order_by('last_name', 'first_name')
        
        # Get search parameters
        query = self.request.GET.get('query', '').strip()
        gender = self.request.GET.get('gender', '')
        min_age = self.request.GET.get('min_age')
        max_age = self.request.GET.get('max_age')
        
        # Apply filters
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(phone_number__icontains=query) |
                Q(email__icontains=query) |
                Q(emergency_contact_name__icontains=query) |
                Q(emergency_contact_phone__icontains=query)
            )
            
        if gender:
            queryset = queryset.filter(gender=gender)
            
        if min_age:
            max_dob = timezone.now().date() - timezone.timedelta(days=365.25 * int(min_age))
            queryset = queryset.filter(date_of_birth__lte=max_dob)
            
        if max_age:
            min_dob = timezone.now().date() - timezone.timedelta(days=365.25 * (int(max_age) + 1))
            queryset = queryset.filter(date_of_birth__gt=min_dob)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = PatientSearchForm(self.request.GET or None)
        return context

class PatientDetailView(StaffRequiredMixin, DetailView):
    """View for displaying patient details"""
    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.get_object()
        
        # Get recent vital signs (last 5)
        context['vital_signs'] = VitalSigns.objects.filter(patient=patient).order_by('-recorded_at')[:5]
        
        # Get recent notes (last 5)
        context['recent_notes'] = PatientNote.objects.filter(patient=patient).order_by('-created_at')[:5]
        
        # Get recent documents (last 5)
        context['recent_documents'] = Document.objects.filter(patient=patient).order_by('-uploaded_at')[:5]
        
        # Check if medical record exists, create if not
        if not hasattr(patient, 'medical_record'):
            MedicalRecord.objects.create(patient=patient)
            
        return context

class PatientCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    """View for creating a new patient"""
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_form.html'
    success_message = _('Patient created successfully')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('patients:detail', kwargs={'pk': self.object.pk})

class PatientUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    """View for updating an existing patient"""
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_form.html'
    success_message = _('Patient updated successfully')
    
    def get_success_url(self):
        return reverse_lazy('patients:detail', kwargs={'pk': self.object.pk})

class PatientDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    """View for deleting a patient"""
    model = Patient
    template_name = 'patients/patient_confirm_delete.html'
    success_url = reverse_lazy('patients:list')
    success_message = _('Patient deleted successfully')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

class PatientDashboardView(StaffRequiredMixin, DetailView):
    """View for patient dashboard with all related information"""
    model = Patient
    template_name = 'patients/patient_dashboard.html'
    context_object_name = 'patient'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.get_object()
        
        # Get medical record (create if not exists)
        medical_record, created = MedicalRecord.objects.get_or_create(patient=patient)
        context['medical_record'] = medical_record
        
        # Get vital signs (paginated)
        vital_signs = VitalSigns.objects.filter(patient=patient).order_by('-recorded_at')
        vital_signs_paginator = Paginator(vital_signs, 10)
        page_number = self.request.GET.get('vital_page')
        context['vital_signs'] = vital_signs_paginator.get_page(page_number)
        
        # Get notes (paginated)
        notes = PatientNote.objects.filter(patient=patient).order_by('-created_at')
        notes_paginator = Paginator(notes, 10)
        page_number = self.request.GET.get('note_page')
        context['notes'] = notes_paginator.get_page(page_number)
        
        # Get documents (paginated)
        documents = Document.objects.filter(patient=patient).order_by('-uploaded_at')
        documents_paginator = Paginator(documents, 10)
        page_number = self.request.GET.get('document_page')
        context['documents'] = documents_paginator.get_page(page_number)
        
        return context

class PatientQuickAddView(LoginRequiredMixin, View):
    """
    View for quickly adding a new patient with minimal information
    """
    def get(self, request, *args, **kwargs):
        form = PatientForm()
        return render(request, 'patients/patient_quick_add.html', {'form': form})
        
    def post(self, request, *args, **kwargs):
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.save()
            messages.success(request, _('Patient added successfully'))
            return redirect('patients:dashboard', pk=patient.pk)
        return render(request, 'patients/patient_quick_add.html', {'form': form})

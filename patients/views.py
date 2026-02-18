from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q

from .forms import PatientForm
from .models import Patient

# Create your views here.

@login_required
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.save()
            messages.success(request, 'Patient saved successfully.')
            return redirect('patients:add')
    else:
        form = PatientForm()

    return render(request, 'patients/patient_form.html', {'form': form})


# Class-based views
class PatientListView(LoginRequiredMixin, ListView):
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Patient.objects.all()
        
        # Search functionality
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(patient_id__icontains=search_query)
            )
        
        # Gender filter
        gender_filter = self.request.GET.get('gender')
        if gender_filter:
            queryset = queryset.filter(gender=gender_filter)
        
        return queryset.order_by('-created_at')


class PatientDetailView(LoginRequiredMixin, DetailView):
    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'
    
    def get_object(self):
        patient_id = self.kwargs.get('patient_id')
        return get_object_or_404(Patient, patient_id=patient_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add questionnaire responses count
        context['questionnaire_responses_count'] = self.object.questionnaire_responses.count()
        return context


class PatientCreateView(LoginRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_form.html'
    success_url = reverse_lazy('patients:list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Patient created successfully!')
        return super().form_valid(form)


class PatientUpdateView(LoginRequiredMixin, UpdateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_form.html'
    
    def get_object(self):
        patient_id = self.kwargs.get('patient_id')
        return get_object_or_404(Patient, patient_id=patient_id)
    
    def get_success_url(self):
        return reverse_lazy('patients:detail', kwargs={'patient_id': self.object.patient_id})
    
    def form_valid(self, form):
        # Save the form directly - no need for commit=False since we're not modifying
        patient = form.save()
        
        # Preserve existing patient_id if it exists
        if self.object.patient_id and not patient.patient_id:
            patient.patient_id = self.object.patient_id
        
        # Set the created_by user if not already set
        if not patient.created_by:
            patient.created_by = self.request.user
        
        messages.success(self.request, 'Patient updated successfully!')
        return super().form_valid(form)


class PatientDeleteView(LoginRequiredMixin, DeleteView):
    model = Patient
    template_name = 'patients/patient_confirm_delete.html'
    success_url = reverse_lazy('patients:list')
    
    def get_object(self):
        patient_id = self.kwargs.get('patient_id')
        return get_object_or_404(Patient, patient_id=patient_id)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Patient deleted successfully!')
        return super().delete(request, *args, **kwargs)


class PatientDashboardView(LoginRequiredMixin, DetailView):
    model = Patient
    template_name = 'patients/patient_dashboard.html'
    context_object_name = 'patient'
    
    def get_object(self):
        patient_id = self.kwargs.get('patient_id')
        return get_object_or_404(Patient, patient_id=patient_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context for the dashboard
        context['questionnaire_responses'] = self.object.questionnaire_responses.all().order_by('-submitted_at')[:5]
        return context


class PatientQuickAddView(LoginRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_quick_add.html'
    success_url = reverse_lazy('patients:list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Patient added successfully!')
        return super().form_valid(form)


# Medical Record View
class MedicalRecordUpdateView(LoginRequiredMixin, UpdateView):
    model = Patient
    template_name = 'patients/medical_record_form.html'
    
    def get_object(self):
        patient_id = self.kwargs.get('patient_id')
        return get_object_or_404(Patient, patient_id=patient_id)
    
    def get_success_url(self):
        return reverse_lazy('patients:detail', kwargs={'patient_id': self.object.patient_id})

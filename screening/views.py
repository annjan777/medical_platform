from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import ScreeningType, ScreeningSession, ScreeningResult, ScreeningAttachment, ScreeningReminder
from .forms import ScreeningTypeForm, ScreeningSessionForm, ScreeningResultForm, ScreeningAttachmentForm
from .serializers import (
    ScreeningTypeSerializer,
    ScreeningSessionSerializer,
    ScreeningResultSerializer,
    ScreeningAttachmentSerializer,
    ScreeningReminderSerializer
)
from patients.models import Patient
from devices.models import Device

# Screening Type Views
class ScreeningTypeListView(LoginRequiredMixin, ListView):
    model = ScreeningType
    template_name = 'screening/screeningtype_list.html'
    context_object_name = 'screening_types'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Add search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(code__iexact=search_query)
            )
        return queryset.order_by('name')


class ScreeningTypeDetailView(LoginRequiredMixin, DetailView):
    model = ScreeningType
    template_name = 'screening/screeningtype_detail.html'
    context_object_name = 'screening_type'


class ScreeningTypeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ScreeningType
    form_class = ScreeningTypeForm
    template_name = 'screening/screeningtype_form.html'
    success_url = reverse_lazy('screening:screening_type_list')
    
    def test_func(self):
        return self.request.user.is_staff
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Screening type created successfully.')
        return super().form_valid(form)


class ScreeningTypeUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ScreeningType
    form_class = ScreeningTypeForm
    template_name = 'screening/screeningtype_form.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_success_url(self):
        messages.success(self.request, 'Screening type updated successfully.')
        return reverse('screening:screening_type_detail', kwargs={'pk': self.object.pk})


class ScreeningTypeDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = ScreeningType
    template_name = 'screening/screeningtype_confirm_delete.html'
    success_url = reverse_lazy('screening:screening_type_list')
    
    def test_func(self):
        return self.request.user.is_staff
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Screening type deleted successfully.')
        return super().delete(request, *args, **kwargs)


# Screening Session Views
class ScreeningSessionListView(LoginRequiredMixin, ListView):
    model = ScreeningSession
    template_name = 'screening/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('patient', 'screening_type', 'conducted_by')
        
        # Filter by status if provided
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(screening_type__name__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
            
        # For non-staff users, only show their own screenings
        if not self.request.user.is_staff:
            queryset = queryset.filter(created_by=self.request.user)
            
        return queryset.order_by('-scheduled_date')


class ScreeningSessionDetailView(LoginRequiredMixin, DetailView):
    model = ScreeningSession
    template_name = 'screening/session_detail.html'
    context_object_name = 'session'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attachments'] = self.object.attachments.all()
        context['results'] = ScreeningResult.objects.filter(session=self.object).first()
        return context


class ScreeningSessionCreateView(LoginRequiredMixin, CreateView):
    model = ScreeningSession
    form_class = ScreeningSessionForm
    template_name = 'screening/session_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Screening session created successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('screening:session_detail', kwargs={'pk': self.object.pk})


class ScreeningSessionUpdateView(LoginRequiredMixin, UpdateView):
    model = ScreeningSession
    form_class = ScreeningSessionForm
    template_name = 'screening/session_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Screening session updated successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('screening:session_detail', kwargs={'pk': self.object.pk})


class ScreeningSessionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = ScreeningSession
    template_name = 'screening/session_confirm_delete.html'
    success_url = reverse_lazy('screening:session_list')
    
    def test_func(self):
        return self.request.user.is_staff
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Screening session deleted successfully.')
        return super().delete(request, *args, **kwargs)


@login_required
def start_screening(request, pk):
    session = get_object_or_404(ScreeningSession, pk=pk)
    
    if not session.can_start():
        messages.error(request, 'This screening cannot be started at this time.')
        return redirect('screening:session_detail', pk=session.pk)

    if not session.consent_obtained:
        messages.error(request, 'Consent is required before starting the screening.')
        return redirect('screening:session_detail', pk=session.pk)

    # Lock device for this session (SRS: one device per session, locked during active session)
    if session.device_used:
        device = session.device_used
        if device.is_locked and device.locked_session_id and device.locked_session_id != str(session.pk):
            messages.error(request, 'Selected device is already locked by another session.')
            return redirect('screening:session_detail', pk=session.pk)
        if device.is_busy and device.locked_session_id and device.locked_session_id != str(session.pk):
            messages.error(request, 'Selected device is currently busy.')
            return redirect('screening:session_detail', pk=session.pk)
        device.is_locked = True
        device.is_busy = True
        device.locked_session_id = str(session.pk)
        device.save(update_fields=['is_locked', 'is_busy', 'locked_session_id'])
    
    session.status = ScreeningSession.STATUS_IN_PROGRESS
    session.actual_start_time = timezone.now()
    session.conducted_by = request.user
    session.save()
    
    messages.success(request, 'Screening session started successfully.')
    return redirect('screening:session_detail', pk=session.pk)


@login_required
def complete_screening(request, pk):
    session = get_object_or_404(ScreeningSession, pk=pk)
    
    if not session.can_complete():
        messages.error(request, 'This screening cannot be completed at this time.')
        return redirect('screening:session_detail', pk=session.pk)
    
    session.status = ScreeningSession.STATUS_COMPLETED
    session.actual_end_time = timezone.now()
    session.save()

    # Unlock device
    if session.device_used:
        device = session.device_used
        if device.locked_session_id == str(session.pk):
            device.is_locked = False
            device.is_busy = False
            device.locked_session_id = ''
            device.save(update_fields=['is_locked', 'is_busy', 'locked_session_id'])
    
    messages.success(request, 'Screening session marked as completed.')
    return redirect('screening:session_detail', pk=session.pk)


@login_required
def cancel_screening(request, pk):
    session = get_object_or_404(ScreeningSession, pk=pk)
    
    if session.status not in [ScreeningSession.STATUS_SCHEDULED, ScreeningSession.STATUS_IN_PROGRESS]:
        messages.error(request, 'Only scheduled or in-progress screenings can be cancelled.')
        return redirect('screening:session_detail', pk=session.pk)
    
    session.status = ScreeningSession.STATUS_CANCELLED
    session.save()

    # Unlock device if this session held the lock
    if session.device_used:
        device = session.device_used
        if device.locked_session_id == str(session.pk):
            device.is_locked = False
            device.is_busy = False
            device.locked_session_id = ''
            device.save(update_fields=['is_locked', 'is_busy', 'locked_session_id'])
    
    messages.success(request, 'Screening session has been cancelled.')
    return redirect('screening:session_detail', pk=session.pk)


# Screening Result Views
class ScreeningResultCreateView(LoginRequiredMixin, CreateView):
    model = ScreeningResult
    form_class = ScreeningResultForm
    template_name = 'screening/result_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.session = get_object_or_404(ScreeningSession, pk=self.kwargs['session_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['session'] = self.session
        return context
    
    def form_valid(self, form):
        form.instance.session = self.session
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Screening result saved successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('screening:session_detail', kwargs={'pk': self.session.pk})


class ScreeningResultDetailView(LoginRequiredMixin, DetailView):
    model = ScreeningResult
    template_name = 'screening/result_detail.html'
    context_object_name = 'result'
    
    def get_queryset(self):
        return super().get_queryset().select_related('session', 'session__patient', 'session__screening_type')


class ScreeningResultUpdateView(LoginRequiredMixin, UpdateView):
    model = ScreeningResult
    form_class = ScreeningResultForm
    template_name = 'screening/result_form.html'
    
    def get_queryset(self):
        return super().get_queryset().select_related('session')
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Screening result updated successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('screening:result_detail', kwargs={'pk': self.object.pk})


# API Views
class ScreeningTypeListAPIView(generics.ListAPIView):
    queryset = ScreeningType.objects.filter(is_active=True)
    serializer_class = ScreeningTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search)
            )
        return queryset


class ScreeningSessionListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ScreeningSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = ScreeningSession.objects.select_related('patient', 'screening_type', 'conducted_by')
        
        # Filter by patient if patient_id is provided
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
            
        # Filter by screening type if type_id is provided
        type_id = self.request.query_params.get('type_id')
        if type_id:
            queryset = queryset.filter(screening_type_id=type_id)
            
        # For non-staff users, only return their own screenings
        if not self.request.user.is_staff:
            queryset = queryset.filter(created_by=self.request.user)
            
        return queryset.order_by('-scheduled_date')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ScreeningSessionRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ScreeningSession.objects.all()
    serializer_class = ScreeningSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(created_by=self.request.user)
        return queryset
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

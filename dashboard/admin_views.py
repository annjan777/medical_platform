from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django import forms

from django.contrib.auth import get_user_model
from patients.models import Patient
from devices.models import Device
from questionnaires.models import Question
from questionnaires.models import Questionnaire
from screening.models import ScreeningSession
from .models import AuditLog, SystemSetting, EmailTemplate

# Get the User model
User = get_user_model()

class SuperuserRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only superusers can access the view."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

# User Management Views
class UserListView(SuperuserRequiredMixin, ListView):
    model = User
    template_name = 'dashboard/admin/users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        return queryset

class UserCreateView(SuperuserRequiredMixin, CreateView):
    model = User
    template_name = 'dashboard/admin/users/user_form.html'
    fields = ['email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'is_superuser']
    success_url = reverse_lazy('dashboard:admin:user_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add password fields to the form
        form.fields['password'] = forms.CharField(
            label='Password',
            widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Enter password'}),
            required=True
        )
        form.fields['password_confirm'] = forms.CharField(
            label='Confirm Password',
            widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirm password'}),
            required=True
        )
        return form
    
    def form_valid(self, form):
        # Validate password confirmation
        password = form.cleaned_data.get('password')
        password_confirm = form.cleaned_data.get('password_confirm')
        
        if password != password_confirm:
            form.add_error('password_confirm', 'Passwords do not match')
            return self.form_invalid(form)
        
        if len(password) < 8:
            form.add_error('password', 'Password must be at least 8 characters long')
            return self.form_invalid(form)
        
        user = form.save(commit=False)
        user.set_password(password)
        user.save()
        messages.success(self.request, f'User {user.email} created successfully.')
        return super().form_valid(form)

class UserUpdateView(SuperuserRequiredMixin, UpdateView):
    model = User
    template_name = 'dashboard/admin/users/user_form.html'
    fields = ['email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'is_superuser']
    
    def get_success_url(self):
        return reverse_lazy('dashboard:admin:user_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'User updated successfully.')
        return super().form_valid(form)

class UserDetailView(SuperuserRequiredMixin, DetailView):
    model = User
    template_name = 'dashboard/admin/users/user_detail.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['devices'] = Device.objects.filter(assigned_to=self.object)
        context['questionnaires'] = Questionnaire.objects.filter(created_by=self.object)
        return context

class UserDeleteView(SuperuserRequiredMixin, DeleteView):
    model = User
    template_name = 'dashboard/admin/users/user_confirm_delete.html'
    success_url = reverse_lazy('dashboard:admin:user_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'User deleted successfully.')
        return super().delete(request, *args, **kwargs)

# Device Management Views
class DeviceListView(SuperuserRequiredMixin, ListView):
    model = Device
    template_name = 'dashboard/admin/devices/device_list.html'
    context_object_name = 'devices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Device.objects.all().order_by('-date_added')
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

class DeviceCreateView(SuperuserRequiredMixin, CreateView):
    model = Device
    template_name = 'dashboard/admin/devices/device_form.html'
    fields = ['name', 'device_id', 'device_type', 'status', 'assigned_to', 'location', 'description']
    success_url = reverse_lazy('dashboard:admin:device_list')
    
    def form_valid(self, form):
        device = form.save()
        messages.success(self.request, f'Device {device.name} added successfully.')
        return super().form_valid(form)

class DeviceUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Device
    template_name = 'dashboard/admin/devices/device_form.html'
    fields = ['name', 'device_id', 'device_type', 'status', 'assigned_to', 'location', 'description']
    
    def get_success_url(self):
        return reverse_lazy('dashboard:admin:device_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Device updated successfully.')
        return super().form_valid(form)

class DeviceDetailView(SuperuserRequiredMixin, DetailView):
    model = Device
    template_name = 'dashboard/admin/devices/device_detail.html'
    context_object_name = 'device'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sessions'] = (
            ScreeningSession.objects.filter(device_used=self.object)
            .order_by('-actual_start_time', '-scheduled_date')[:5]
        )
        return context

class DeviceDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Device
    template_name = 'dashboard/admin/devices/device_confirm_delete.html'
    success_url = reverse_lazy('dashboard:admin:device_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Device deleted successfully.')
        return super().delete(request, *args, **kwargs)

# System Settings Views
class SystemSettingsView(SuperuserRequiredMixin, TemplateView):
    template_name = 'dashboard/admin/settings/system.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any system settings to the context
        return context

class EmailSettingsView(SuperuserRequiredMixin, TemplateView):
    template_name = 'dashboard/admin/settings/email.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add email settings to the context
        return context

class APIKeysView(SuperuserRequiredMixin, TemplateView):
    template_name = 'dashboard/admin/settings/api_keys.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add API keys to the context
        return context

# Audit Logs View
class AuditLogListView(SuperuserRequiredMixin, ListView):
    template_name = 'dashboard/admin/audit_logs.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    def get_queryset(self):
        # This would typically come from an AuditLog model
        # For now, return an empty queryset
        return []

# Helper functions
def get_recent_activities(limit=10):
    """Retrieve recent system activities for the admin dashboard."""
    # This would typically come from an AuditLog model
    # For now, return sample data
    return [
        {
            'icon': 'user-plus',
            'title': 'New user registered',
            'description': 'John Doe (john@example.com) created an account',
            'timestamp': timezone.now() - timedelta(minutes=15)
        },
        {
            'icon': 'microchip',
            'title': 'Device connected',
            'description': 'Device ID: DEV-12345 connected successfully',
            'timestamp': timezone.now() - timedelta(hours=1)
        },
        {
            'icon': 'clipboard-check',
            'title': 'Screening completed',
            'description': 'Screening #00421 completed by Dr. Smith',
            'timestamp': timezone.now() - timedelta(hours=2)
        },
    ][:limit]

def get_system_health():
    """Check and return system health status."""
    # This would check various system components
    return {
        'database': 'online',
        'storage': 'normal',
        'api_status': 'operational',
        'last_checked': timezone.now(),
    }

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    """Main admin dashboard view with system overview and quick stats."""
    # Get user statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    # Get patient statistics
    total_patients = Patient.objects.count()
    
    # Get device statistics
    total_devices = Device.objects.count()
    active_devices = Device.objects.filter(status=Device.STATUS_ACTIVE).count()
    
    # Get screening statistics
    total_screenings = ScreeningSession.objects.count()
    recent_screenings = ScreeningSession.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    recent_screenings_list = (
        ScreeningSession.objects.select_related('patient', 'device_used')
        .order_by('-created_at')[:5]
    )
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'new_users': new_users,
        'total_patients': total_patients,
        'active_patients': total_patients,  # All patients are considered active
        'total_devices': total_devices,
        'active_devices': active_devices,
        'total_screenings': total_screenings,
        'recent_screenings': recent_screenings,
        'recent_screenings_list': recent_screenings_list,
        'recent_activities': get_recent_activities(),
        'system_health': get_system_health(),
    }
    
    return render(request, 'dashboard/admin/dashboard.html', context)


class AuditLogListView(SuperuserRequiredMixin, ListView):
    model = AuditLog
    template_name = 'dashboard/admin/audit_logs.html'
    context_object_name = 'audit_logs'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = AuditLog.objects.select_related('user').order_by('-timestamp')
        
        # Filter by action type
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by user
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_choices'] = AuditLog.ACTION_TYPES
        context['users'] = User.objects.all()
        
        # Add statistics
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        context['today_logs'] = AuditLog.objects.filter(timestamp__date=now.date()).count()
        context['week_logs'] = AuditLog.objects.filter(timestamp__gte=now - timedelta(days=7)).count()
        context['month_logs'] = AuditLog.objects.filter(timestamp__gte=now - timedelta(days=30)).count()
        
        return context


class SystemSettingsView(SuperuserRequiredMixin, TemplateView):
    template_name = 'dashboard/admin/system_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = SystemSetting.objects.all()
        return context


class EmailSettingsView(SuperuserRequiredMixin, TemplateView):
    template_name = 'dashboard/admin/email_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email_templates'] = EmailTemplate.objects.all()
        return context


class APIKeysView(SuperuserRequiredMixin, TemplateView):
    template_name = 'dashboard/admin/api_keys.html'

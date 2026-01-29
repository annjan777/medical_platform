from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models import Count, Q
from django.contrib.contenttypes.models import ContentType
from django.utils.decorators import method_decorator
from django.views.generic import ListView, UpdateView, CreateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_http_methods
from functools import wraps
from datetime import timedelta

User = get_user_model()

def admin_required(view_func):
    """
    Decorator for views that checks that the user is an admin or staff,
    redirecting to the login page if necessary.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_staff or request.user.is_superuser):
            return HttpResponseForbidden("You don't have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
def dashboard(request):
    # If user is staff or superuser, redirect to admin dashboard
    if request.user.is_staff or request.user.is_superuser:
        return redirect('dashboard:admin_dashboard')
    # For regular users, redirect to patients app
    return redirect('patients:add')

@method_decorator([login_required, admin_required], name='dispatch')
class AdminDashboardView(ListView):
    template_name = 'admin/dashboard/dashboard.html'
    context_object_name = 'recent_users'
    paginate_by = 10
    
    def get_queryset(self):
        return User.objects.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user statistics
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()
        context['staff_users'] = User.objects.filter(is_staff=True).count()
        context['superusers'] = User.objects.filter(is_superuser=True).count()
        
        # Get recent users (already handled by ListView)
        context['recent_users'] = self.get_queryset()[:5]
        
        # Get group statistics
        context['groups'] = Group.objects.annotate(
            user_count=Count('user')
        ).order_by('-user_count')[:5]
        
        # Get recent activity logs if you have a logging system
        try:
            from django.contrib.admin.models import LogEntry
            user_type = ContentType.objects.get_for_model(User)
            context['recent_activity'] = LogEntry.objects.filter(
                content_type=user_type
            ).select_related('user').order_by('-action_time')[:5]
        except:
            context['recent_activity'] = []
        
        return context

# User Management Views
@method_decorator([login_required, admin_required], name='dispatch')
class UserListView(ListView):
    model = User
    template_name = 'admin/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = User.objects.all()
        
        # Search
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status == 'staff':
            queryset = queryset.filter(is_staff=True)
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()
        context['staff_users'] = User.objects.filter(is_staff=True).count()
        return context

@method_decorator([login_required, admin_required], name='dispatch')
class UserCreateView(CreateView):
    model = User
    template_name = 'admin/user_form.html'
    fields = ['email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'groups']
    success_url = reverse_lazy('admin_user_list')
    
    def form_valid(self, form):
        # Generate a random password
        import random
        import string
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        user = form.save(commit=False)
        user.set_password(password)
        user.save()
        form.save_m2m()  # Save many-to-many data
        
        # Send welcome email with credentials
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            subject = 'Your HealthScreener Pro Account Has Been Created'
            message = f'''Hello {user.get_full_name() or user.email},
            
Your account has been created by an administrator. Here are your login details:

Email: {user.email}
Password: {password}

Please log in and change your password immediately.

Best regards,
HealthScreener Pro Team'''
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            messages.success(self.request, f'User {user.email} created successfully. A welcome email has been sent.')
        except Exception as e:
            messages.warning(self.request, f'User created but could not send email: {str(e)}')
        
        return super().form_valid(form)

@method_decorator([login_required, admin_required], name='dispatch')
class UserUpdateView(UpdateView):
    model = User
    template_name = 'admin/user_form.html'
    fields = ['email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'groups']
    
    def get_success_url(self):
        return reverse('admin_user_detail', args=[self.object.id])
    
    def form_valid(self, form):
        messages.success(self.request, f'User {self.object.email} updated successfully.')
        return super().form_valid(form)

@method_decorator([login_required, admin_required], name='dispatch')
class UserDetailView(DetailView):
    model = User
    template_name = 'admin/user_detail.html'
    context_object_name = 'user_detail'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = self.object.user_permissions.all()
        context['user_groups'] = self.object.groups.all()
        
        # Get user activity log if available
        try:
            from django.contrib.admin.models import LogEntry
            from django.contrib.contenttypes.models import ContentType
            
            user_type = ContentType.objects.get_for_model(User)
            context['user_activity'] = LogEntry.objects.filter(
                content_type=user_type,
                object_id=self.object.id
            ).order_by('-action_time')[:20]
        except:
            context['user_activity'] = []
            
        return context

@method_decorator([login_required, admin_required], name='dispatch')
class UserDeleteView(DeleteView):
    model = User
    template_name = 'admin/user_confirm_delete.html'
    success_url = reverse_lazy('admin_user_list')
    
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        username = user.email
        user.delete()
        messages.success(request, f'User {username} has been deleted.')
        return redirect(self.get_success_url())

@login_required
@admin_required
@require_http_methods(['POST'])
def toggle_user_status(request, pk):
    """Toggle user active status via AJAX."""
    user = get_object_or_404(User, pk=pk)
    user.is_active = not user.is_active
    user.save()
    
    return JsonResponse({
        'status': 'success',
        'is_active': user.is_active,
        'message': f"User {'activated' if user.is_active else 'deactivated'} successfully."
    })


def get_recent_activities(limit=10):
    """Retrieve recent system activities for the admin dashboard."""
    # This would typically come from an audit log model
    # For now, we'll return a placeholder
    return []


def get_system_health():
    """Check and return system health status."""
    # This would check various system components
    # For now, we'll return a placeholder
    return {
        'database': 'online',
        'storage': 'normal',
        'api_status': 'operational',
        'last_checked': timezone.now(),
    }

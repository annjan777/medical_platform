from django.urls import path, include
from django.contrib.auth.decorators import login_required, user_passes_test
from . import views
from .views import AdminDashboardView

def admin_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_superuser,
        login_url='login',
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

app_name = 'dashboard'

urlpatterns = [
    # Regular user dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Admin dashboard (for staff/superusers)
    path('admin_dashboard/', admin_required(AdminDashboardView.as_view()), name='admin_dashboard'),

    # New custom admin UI (SRS): /dashboard/admin/...
    path('admin/', include(('dashboard.admin_urls', 'admin'), namespace='admin')),
]

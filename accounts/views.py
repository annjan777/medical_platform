from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth import logout

# Create your views here.

def home(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('dashboard:admin_dashboard')
        elif hasattr(request.user, 'role') and request.user.role == 'HEALTH_ASSISTANT':
            return redirect('health_assistant:home')
        elif request.user.is_staff:
            return redirect('dashboard:admin_dashboard')
        else:
            return redirect('patients:add')
    return render(request, 'public/home.html')


class MedicalLoginView(LoginView):
    template_name = 'registration/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('dashboard:admin_dashboard')
            elif hasattr(request.user, 'role') and request.user.role == 'HEALTH_ASSISTANT':
                return redirect('health_assistant:home')
            elif request.user.is_staff:
                return redirect('dashboard:admin_dashboard')
            else:
                return redirect('patients:add')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser:
            return reverse('dashboard:admin_dashboard')
        elif hasattr(user, 'role') and user.role == 'HEALTH_ASSISTANT':
            return reverse('health_assistant:home')
        elif user.is_staff:
            return reverse('dashboard:admin_dashboard')
        else:
            return reverse('patients:add')


def custom_logout(request):
    """Custom logout that mimics Django admin logout behavior"""
    logout(request)
    return redirect('/')

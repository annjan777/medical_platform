from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

# Create your views here.

def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('dashboard:admin_dashboard')
        return redirect('patients:add')
    return render(request, 'public/home.html')


class MedicalLoginView(LoginView):
    template_name = 'registration/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return redirect('dashboard:admin_dashboard')
            return redirect('patients:add')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return reverse('dashboard:admin_dashboard')
        return reverse('patients:add')

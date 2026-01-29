from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse

class CustomLoginView(LoginView):
    def get_success_url(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return reverse('admin:index')  # Redirect to admin dashboard
        return super().get_success_url()

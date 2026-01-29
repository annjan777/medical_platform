from django.shortcuts import redirect
from django.urls import reverse

class AdminRedirectMiddleware:
    """
    Middleware to redirect staff/superusers from the default Django admin to the custom admin.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the response from the next middleware/view
        response = self.get_response(request)
        
        # Check if the user is trying to access the default Django admin
        if (request.path.startswith('/django-admin/') and 
            request.user.is_authenticated and 
            (request.user.is_staff or request.user.is_superuser)):
            # Redirect to our custom admin dashboard
            return redirect('dashboard:admin_dashboard')
            
        return response

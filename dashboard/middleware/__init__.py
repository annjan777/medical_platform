# Import the middleware class to make it available when importing from dashboard.middleware
from .admin_redirect import AdminRedirectMiddleware

# This makes the middleware available when importing from dashboard.middleware
__all__ = ['AdminRedirectMiddleware']

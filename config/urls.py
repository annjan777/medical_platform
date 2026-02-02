"""
config URL Configuration
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from accounts.views import MedicalLoginView, home
from .admin import admin_site

urlpatterns = [
    path("", home, name="home"),

    # =========================
    # Admin (Custom AdminSite)
    # =========================
    path("admin/", admin_site.urls),

    # =========================
    # Authentication
    # =========================
    path("login/", MedicalLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),

    # =========================
    # Dashboards
    # =========================
    path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
    path("health-assistant/", include(("health_assistant.urls", "health_assistant"), namespace="health_assistant")),

    # =========================
    # Patients
    # =========================
    path("patients/", include(("patients.urls", "patients"), namespace="patients")),

    # =========================
    # Screening + Questionnaires
    # =========================
    path("screening/", include(("screening.urls", "screening"), namespace="screening")),
    path("questionnaires/", include(("questionnaires.urls", "questionnaires"), namespace="questionnaires")),

]

# =========================
# Static & Media (DEV only)
# =========================
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Debug toolbar
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns

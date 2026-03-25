from django.urls import path
from . import views

urlpatterns = [
    path("ping/", views.session_ping, name="session_ping"),
]

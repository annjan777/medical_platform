from django.urls import path
from . import views, api_views

app_name = 'doctor'

urlpatterns = [
    path('', views.doctor_home, name='home'),
    path('patients/', views.PatientListView.as_view(), name='patient_list'),
    path('patients/<int:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
    path('consultations/pending/', views.PendingConsultationListView.as_view(), name='pending_consultations'),
    path('consultations/completed/', views.CompletedConsultationListView.as_view(), name='completed_consultations'),
    path('responses/', views.ResponseListView.as_view(), name='response_list'),
    path('responses/<int:pk>/', views.ResponseDetailView.as_view(), name='response_detail'),
    path('responses/<int:pk>/view/', views.ResponseReadOnlyView.as_view(), name='response_readonly'),
    path('prescription/<int:document_id>/download/', views.download_prescription, name='download_prescription'),
    path('sessions/', views.SessionListView.as_view(), name='session_list'),
    path('annotations/', views.AnnotationListView.as_view(), name='annotation_list'),
    
    # API endpoints
    path('api/prescription/<str:identifier>/', api_views.setu_prescription_api, name='api_fetch_prescription'),
]

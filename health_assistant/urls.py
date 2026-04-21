from django.urls import path
from . import views

app_name = 'health_assistant'

urlpatterns = [
    # Home Page - Main Health Assistant Entry Point
    path('', views.home_page, name='home'),
    
    # Dedicated Pages
    path('questionnaires/', views.questionnaires_page, name='questionnaires'),
    path('landing/', views.landing_page, name='landing'),
    path('patients/', views.patient_list, name='patient_list'),
    
    # Dashboard (legacy - can be removed if not needed)
    path('dashboard/', views.HealthAssistantDashboardView.as_view(), name='dashboard'),
    
    # Medical Records
    path('patient/register/', views.patient_register, name='patient_register'),
    
    # Screening Sessions
    path('screening/', views.screening_session, name='screening_session'),
    path('screening/<int:patient_id>/', views.screening_session, name='screening_with_patient'),
    path('session/<str:session_id>/', views.session_detail, name='session_detail'),
    path('session/<str:session_id>/overview/', views.session_overview, name='session_overview'),
    path('session/<str:session_id>/attachments/<int:attachment_id>/', views.session_attachment_view, name='session_attachment_view'),
    path('session/<str:session_id>/attachments/<int:attachment_id>/zip-entry/', views.session_zip_entry_view, name='session_zip_entry_view'),
    path('sessions/', views.my_sessions, name='my_sessions'),
    
    # API Endpoints
    path('api/today-stats/', views.api_today_stats, name='api_today_stats'),
    path('api/recent-activity/', views.api_recent_activity, name='api_recent_activity'),
    path('api/search-patients/', views.api_search_patients, name='api_search_patients'),
    path('api/test-auth/', views.api_test_auth, name='api_test_auth'),
    path('api/get-patient/<int:patient_id>/', views.api_get_patient, name='api_get_patient'),
    path('api/patients/<int:patient_id>/update/', views.api_patient_update, name='api_patient_update'),
    path('api/get-products/', views.api_get_products, name='api_get_products'),
    path('api/get-product/<int:product_id>/', views.api_get_product, name='api_get_product'),
    path('api/get-devices/', views.api_get_devices, name='api_get_devices'),
    path('api/reset-devices/', views.api_reset_devices_disconnected, name='api_reset_devices'),
    path('api/get-device/<int:device_id>/', views.api_get_device, name='api_get_device'),
    path('api/create-session/', views.api_create_session, name='api_create_session'),
    path('api/submit-questionnaire/', views.api_submit_questionnaire, name='api_submit_questionnaire'),
    path('api/save-vitals/', views.api_save_vitals, name='api_save_vitals'),
    path('api/session/<str:session_id>/associate-device/', views.api_associate_device, name='api_associate_device'),
]

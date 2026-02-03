from django.urls import path
from .views import (
    # Patient views
    PatientListView, PatientDetailView, PatientCreateView, 
    PatientUpdateView, PatientDeleteView, PatientDashboardView, PatientQuickAddView,
    
    # Medical record views
    MedicalRecordUpdateView,
    
    # Vital signs views
    VitalSignsCreateView, VitalSignsUpdateView, VitalSignsDeleteView,
    
    # Patient note views
    PatientNoteCreateView, PatientNoteUpdateView, PatientNoteDeleteView,
    
    # Document views
    DocumentUploadView, DocumentUpdateView, DocumentDeleteView, DocumentDownloadView
)

app_name = 'patients'

urlpatterns = [
    # Patient URLs
    path('', PatientListView.as_view(), name='list'),
    path('add/', PatientCreateView.as_view(), name='add'),
    path('quick-add/', PatientQuickAddView.as_view(), name='quick_add'),
    path('<str:patient_id>/', PatientDetailView.as_view(), name='detail'),
    path('<str:patient_id>/update/', PatientUpdateView.as_view(), name='update'),
    path('<str:patient_id>/delete/', PatientDeleteView.as_view(), name='delete'),
    path('<str:patient_id>/dashboard/', PatientDashboardView.as_view(), name='dashboard'),
    
    # Medical Record URLs
    path('<str:patient_id>/medical-record/', MedicalRecordUpdateView.as_view(), name='medical_record_update'),
    
    # Vital Signs URLs
    path('<str:patient_id>/vitals/add/', VitalSignsCreateView.as_view(), name='vitals_add'),
    path('<str:patient_id>/vitals/<int:pk>/update/', VitalSignsUpdateView.as_view(), name='vitals_update'),
    path('<str:patient_id>/vitals/<int:pk>/delete/', VitalSignsDeleteView.as_view(), name='vitals_delete'),
    
    # Patient Note URLs
    path('<str:patient_id>/notes/add/', PatientNoteCreateView.as_view(), name='note_add'),
    path('<str:patient_id>/notes/<int:pk>/update/', PatientNoteUpdateView.as_view(), name='note_update'),
    path('<str:patient_id>/notes/<int:pk>/delete/', PatientNoteDeleteView.as_view(), name='note_delete'),
    
    # Document URLs
    path('<str:patient_id>/documents/upload/', DocumentUploadView.as_view(), name='document_upload'),
    path('<str:patient_id>/documents/<int:pk>/update/', DocumentUpdateView.as_view(), name='document_update'),
    path('<str:patient_id>/documents/<int:pk>/delete/', DocumentDeleteView.as_view(), name='document_delete'),
    path('<str:patient_id>/documents/<int:pk>/download/', DocumentDownloadView.as_view(), name='document_download'),
]

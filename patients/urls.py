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
    path('<int:pk>/', PatientDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', PatientUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', PatientDeleteView.as_view(), name='delete'),
    path('<int:pk>/dashboard/', PatientDashboardView.as_view(), name='dashboard'),
    
    # Medical Record URLs
    path('<int:patient_pk>/medical-record/', MedicalRecordUpdateView.as_view(), name='medical_record_update'),
    
    # Vital Signs URLs
    path('<int:patient_pk>/vitals/add/', VitalSignsCreateView.as_view(), name='vitals_add'),
    path('<int:patient_pk>/vitals/<int:pk>/update/', VitalSignsUpdateView.as_view(), name='vitals_update'),
    path('<int:patient_pk>/vitals/<int:pk>/delete/', VitalSignsDeleteView.as_view(), name='vitals_delete'),
    
    # Patient Note URLs
    path('<int:patient_pk>/notes/add/', PatientNoteCreateView.as_view(), name='note_add'),
    path('<int:patient_pk>/notes/<int:pk>/update/', PatientNoteUpdateView.as_view(), name='note_update'),
    path('<int:patient_pk>/notes/<int:pk>/delete/', PatientNoteDeleteView.as_view(), name='note_delete'),
    
    # Document URLs
    path('<int:patient_pk>/documents/upload/', DocumentUploadView.as_view(), name='document_upload'),
    path('<int:patient_pk>/documents/<int:pk>/update/', DocumentUpdateView.as_view(), name='document_update'),
    path('<int:patient_pk>/documents/<int:pk>/delete/', DocumentDeleteView.as_view(), name='document_delete'),
    path('<int:patient_pk>/documents/<int:pk>/download/', DocumentDownloadView.as_view(), name='document_download'),
]

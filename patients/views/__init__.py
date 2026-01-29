# Import all views from their respective modules
from .patient_views import (
    PatientListView, PatientDetailView, PatientCreateView,
    PatientUpdateView, PatientDeleteView, PatientDashboardView, PatientQuickAddView
)

from .medical_record_views import (
    MedicalRecordUpdateView,
    VitalSignsCreateView, VitalSignsUpdateView, VitalSignsDeleteView,
    PatientNoteCreateView, PatientNoteUpdateView, PatientNoteDeleteView,
    DocumentUploadView, DocumentUpdateView, DocumentDeleteView, DocumentDownloadView
)

# Make all views available when importing from patients.views
__all__ = [
    'PatientListView', 'PatientDetailView', 'PatientCreateView',
    'PatientUpdateView', 'PatientDeleteView', 'PatientDashboardView', 'PatientQuickAddView',
    'MedicalRecordUpdateView',
    'VitalSignsCreateView', 'VitalSignsUpdateView', 'VitalSignsDeleteView',
    'PatientNoteCreateView', 'PatientNoteUpdateView', 'PatientNoteDeleteView',
    'DocumentUploadView', 'DocumentUpdateView', 'DocumentDeleteView', 'DocumentDownloadView'
]
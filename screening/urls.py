from django.urls import path
from . import views

app_name = 'screening'

urlpatterns = [
    # Screening Type URLs
    path('types/', views.ScreeningTypeListView.as_view(), name='screening_type_list'),
    path('types/create/', views.ScreeningTypeCreateView.as_view(), name='screening_type_create'),
    path('types/<int:pk>/', views.ScreeningTypeDetailView.as_view(), name='screening_type_detail'),
    path('types/<int:pk>/update/', views.ScreeningTypeUpdateView.as_view(), name='screening_type_update'),
    path('types/<int:pk>/delete/', views.ScreeningTypeDeleteView.as_view(), name='screening_type_delete'),
    
    # Screening Session URLs
    path('sessions/', views.ScreeningSessionListView.as_view(), name='session_list'),
    path('sessions/create/', views.ScreeningSessionCreateView.as_view(), name='session_create'),
    path('sessions/<int:pk>/', views.ScreeningSessionDetailView.as_view(), name='session_detail'),
    path('sessions/<int:pk>/update/', views.ScreeningSessionUpdateView.as_view(), name='session_update'),
    path('sessions/<int:pk>/delete/', views.ScreeningSessionDeleteView.as_view(), name='session_delete'),
    path('sessions/<int:pk>/start/', views.start_screening, name='session_start'),
    path('sessions/<int:pk>/complete/', views.complete_screening, name='session_complete'),
    path('sessions/<int:pk>/cancel/', views.cancel_screening, name='session_cancel'),
    
    # Screening Result URLs
    path('sessions/<int:session_pk>/result/', views.ScreeningResultCreateView.as_view(), name='result_create'),
    path('results/<int:pk>/', views.ScreeningResultDetailView.as_view(), name='result_detail'),
    path('results/<int:pk>/update/', views.ScreeningResultUpdateView.as_view(), name='result_update'),
    
    # API Endpoints
    path('api/screening-types/', views.ScreeningTypeListAPIView.as_view(), name='api_screening_type_list'),
    path('api/sessions/', views.ScreeningSessionListCreateAPIView.as_view(), name='api_session_list_create'),
    path('api/sessions/<int:pk>/', views.ScreeningSessionRetrieveUpdateDestroyAPIView.as_view(), 
         name='api_session_retrieve_update_destroy'),
]

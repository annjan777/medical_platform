from django.urls import path
from . import views

app_name = 'iot_gateway'

urlpatterns = [
    path('receive-text/', views.receive_text_data, name='receive_text'),
    path('receive-image/', views.receive_image_data, name='receive_image'),
    path('server-info/', views.get_server_info, name='server_info'),
    path('check-session-data/<str:session_id>/', views.check_session_data, name='check_session_data'),
    path('trigger-scan/<str:session_id>/', views.trigger_scan, name='trigger_scan'),
    path('ping-device/<int:device_id>/', views.ping_device, name='ping_device'),
    
    # Phase 3: APIs
    path('device/<int:device_id>/assign/', views.assign_device, name='assign_device'),
    path('device/<int:device_id>/release/', views.release_device, name='release_device'),
    path('session/upload/init/', views.upload_init, name='upload_init'),
    path('session/upload/done/', views.upload_done, name='upload_done'),
]

from django.urls import path

from . import admin_views


app_name = "admin"


urlpatterns = [
    path("", admin_views.admin_dashboard, name="dashboard"),

    # Users
    path("users/", admin_views.UserListView.as_view(), name="user_list"),
    path("users/create/", admin_views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/", admin_views.UserDetailView.as_view(), name="user_detail"),
    path("users/<int:pk>/update/", admin_views.UserUpdateView.as_view(), name="user_update"),
    path("users/<int:pk>/delete/", admin_views.UserDeleteView.as_view(), name="user_delete"),

    # Devices
    path("devices/", admin_views.DeviceListView.as_view(), name="device_list"),
    path("devices/create/", admin_views.DeviceCreateView.as_view(), name="device_create"),
    path("devices/<int:pk>/", admin_views.DeviceDetailView.as_view(), name="device_detail"),
    path("devices/<int:pk>/update/", admin_views.DeviceUpdateView.as_view(), name="device_update"),
    path("devices/<int:pk>/delete/", admin_views.DeviceDeleteView.as_view(), name="device_delete"),

    # Settings / audit (placeholders)
    path("settings/system/", admin_views.SystemSettingsView.as_view(), name="system_settings"),
    path("settings/email/", admin_views.EmailSettingsView.as_view(), name="email_settings"),
    path("settings/api-keys/", admin_views.APIKeysView.as_view(), name="api_keys"),
    path("audit-logs/", admin_views.AuditLogListView.as_view(), name="audit_logs"),
]


from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from .models import AuditLog, SystemSetting, EmailTemplate

# Get the User model
User = get_user_model()

# Unregister the default User admin if it's already registered
if admin.site.is_registered(User):
    admin.site.unregister(User)

# Unregister Group model if you don't need it in admin
admin.site.unregister(Group)

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'model', 'object_repr', 'user', 'timestamp')
    list_filter = ('action', 'model', 'timestamp')
    search_fields = ('object_repr', 'user__username', 'ip_address')
    readonly_fields = ('user', 'action', 'model', 'object_id', 'object_repr', 'changes', 'ip_address', 'timestamp')
    date_hierarchy = 'timestamp'

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'is_public', 'updated_at')
    list_editable = ('value', 'is_public')
    search_fields = ('key', 'description')
    list_filter = ('is_public',)

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'is_active', 'updated_at')
    list_editable = ('is_active',)
    search_fields = ('name', 'subject', 'content')
    list_filter = ('is_active',)

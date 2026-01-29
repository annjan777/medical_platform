from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.models import Group
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, include, reverse
from django.utils.html import escape
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from functools import update_wrapper
from django.core.exceptions import PermissionDenied

# Get custom user model
User = get_user_model()


# -------------------------
# Custom Admin Site
# -------------------------
class CustomAdminSite(admin.AdminSite):
    site_header = "Medical Platform Admin"
    site_title = "Medical Platform Admin"
    index_title = "Welcome to Medical Platform Admin"

    def get_urls(self):
        # Get default admin URLs first
        urls = super().get_urls()
        
        # Add our custom URLs with admin view wrapper
        custom_urls = [
            path(
                "password_reset/",
                self.admin_view(PasswordResetView.as_view()),
                name="password_reset",
            ),
            path(
                "password_reset/done/",
                self.admin_view(PasswordResetDoneView.as_view()),
                name="password_reset_done",
            ),
            path(
                "reset/<uidb64>/<token>/",
                self.admin_view(PasswordResetConfirmView.as_view()),
                name="password_reset_confirm",
            ),
            path(
                "reset/done/",
                self.admin_view(PasswordResetCompleteView.as_view()),
                name="password_reset_complete",
            ),
            # Include auth URLs with admin view wrapper
            path('', include('django.contrib.auth.urls')),
        ]

        return custom_urls + urls

    def each_context(self, request):
        context = super().each_context(request)
        context["site_url"] = "/admin/"
        return context


class CustomUserAdmin(BaseUserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "role")
    ordering = ("email",)
    filter_horizontal = ("groups", "user_permissions",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "phone_number", "role")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login",)}),  # Removed date_joined as it's auto-set
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role', 'is_staff', 'is_superuser', 'is_active', 'groups'),
        }),
    )
    
    def get_urls(self):
        from django.urls import path
        
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self
            return update_wrapper(wrapper, view)
            
        return [
            path(
                '<id>/password/',
                wrap(self.user_change_password),
                name='auth_user_password_change',
            ),
        ] + super().get_urls()
    
    @method_decorator(csrf_protect)
    def user_change_password(self, request, id, form_url=''):
        user = self.get_object(request, id)
        if not self.has_change_permission(request, user):
            raise PermissionDenied
        
        if user is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {
                'name': self.model._meta.verbose_name,
                'key': id,
            })
            
        if request.method == 'POST':
            form = self.change_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                change_message = self.construct_change_message(request, form, None)
                self.log_change(request, user, change_message)
                msg = _('Password changed successfully.')
                messages.success(request, msg)
                return self.response_change(request, user)
        else:
            form = self.change_password_form(user)

        fieldsets = [(None, {'fields': list(form.base_fields)}),]
        admin_form = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            'title': _('Change password: %s') % escape(user.get_username()),
            'adminForm': admin_form,
            'form_url': form_url,
            'form': form,
            'is_popup': ('_popup' in request.POST or
                         '_popup' in request.GET),
            'is_popup_var': '_popup',
            'add': True,
            'change': False,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_absolute_url': False,
            'opts': self.model._meta,
            'original': user,
            'save_as': False,
            'show_save': True,
            **self.admin_site.each_context(request),
        }

        request.current_app = self.admin_site.name

        return TemplateResponse(
            request,
            self.change_user_password_template or 'admin/auth/user/change_password.html',
            context,
        )


# Create an instance of our custom admin site
admin_site = CustomAdminSite(name='admin')

# Register the User model with our custom UserAdmin
admin_site.register(User, CustomUserAdmin)

# Register the Group model with the default GroupAdmin
from django.contrib.auth.models import Group
admin_site.register(Group, admin.ModelAdmin)

# Set the default admin site to our custom admin site
admin.site = admin_site

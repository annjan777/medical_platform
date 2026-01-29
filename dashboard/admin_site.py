from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class CustomAdminSite(AdminSite):
    site_header = _('HealthScreener Pro Admin')
    site_title = _('HealthScreener Pro Admin Portal')
    index_title = _('Dashboard')
    site_url = '/dashboard/'

custom_admin_site = CustomAdminSite(name='custom_admin')

from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class CustomAdminSite(AdminSite):
    site_header = _('Medical Data Collection Platform Admin')
    site_title = _('Medical Data Collection Platform Admin Portal')
    index_title = _('Dashboard')
    site_url = '/dashboard/'

custom_admin_site = CustomAdminSite(name='custom_admin')

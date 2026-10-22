from django.apps import AppConfig


class DashboardConfig(AppConfig):
    name = 'dashboard'
    verbose_name = 'Nocturn Haven'

    def ready(self):
        """Apply Nocturn Haven branding to the Django admin site."""
        from django.contrib import admin

        admin.site.site_header = 'Nocturn Haven'
        admin.site.site_title = 'Nocturn Haven · Hotel Operations'
        admin.site.index_title = 'Hotel Operations Console'

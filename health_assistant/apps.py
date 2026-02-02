from django.apps import AppConfig


class HealthAssistantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'health_assistant'
    verbose_name = 'Health Assistant Portal'
    
    def ready(self):
        # Import signals when the app is ready
        try:
            from . import signals
        except ImportError:
            pass

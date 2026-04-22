from django.apps import AppConfig
from django.conf import settings


class IotGatewayConfig(AppConfig):
    name = 'iot_gateway'
    verbose_name = 'IoT Gateway'
    _mqtt_started = False  # class-level flag to prevent double-start

    def ready(self):
        """
        Called once when Django finishes loading all apps.
        Starts the MQTT listener as a background thread automatically.
        Works with both `manage.py runserver` and gunicorn.
        """
        if not settings.MQTT_ENABLED:
            return

        import sys

        # Skip for management commands that don't need the listener
        skip_commands = {
            'migrate', 'makemigrations', 'collectstatic', 'shell',
            'createsuperuser', 'flush', 'dumpdata', 'loaddata',
            'mqtt_status_listener', 'check', 'test',
        }
        if sys.argv and len(sys.argv) > 1 and sys.argv[1] in skip_commands:
            return

        # Prevent double-start (Django dev server calls ready() twice due to reloader)
        if IotGatewayConfig._mqtt_started:
            return
        IotGatewayConfig._mqtt_started = True

        from iot_gateway.mqtt_listener import start_listener
        start_listener()

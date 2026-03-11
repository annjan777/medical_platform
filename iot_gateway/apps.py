import os
from django.apps import AppConfig


class IotGatewayConfig(AppConfig):
    name = 'iot_gateway'
    verbose_name = 'IoT Gateway'

    def ready(self):
        """
        Called once when Django finishes loading all apps.
        Starts the MQTT listener as a background thread automatically —
        no need to run `python3 manage.py mqtt_status_listener` manually.

        Guarded against:
        - Double-start from Django's dev server auto-reloader
        - manage.py commands that don't need the listener (migrate, shell, etc.)
        """
        # Don't start during manage.py commands like migrate, collectstatic, shell
        import sys
        skip_commands = {'migrate', 'makemigrations', 'collectstatic', 'shell',
                         'createsuperuser', 'flush', 'dumpdata', 'loaddata',
                         'mqtt_status_listener'}  # avoid double-start if run manually
        if sys.argv and len(sys.argv) > 1 and sys.argv[1] in skip_commands:
            return

        # Avoid double-start in Django's dev-server reloader child process
        if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('DJANGO_SETTINGS_MODULE'):
            # RUN_MAIN=true means we're the actual server process (not the reloader watcher)
            from iot_gateway.mqtt_listener import start_listener
            start_listener()

import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from devices.models import Device
from django.conf import settings

class Command(BaseCommand):
    help = 'Runs a background loop to verify device health and timeout inactive ones'

    def handle(self, *args, **options):
        if not settings.MQTT_ENABLED:
            self.stdout.write(self.style.WARNING("MQTT is disabled"))
            return

        import paho.mqtt.client as mqtt

        broker = settings.MQTT_BROKER_URL
        port = settings.MQTT_BROKER_PORT
        
        # Setup publisher client to send pings
        client = mqtt.Client(client_id="django_health_monitor", clean_session=True)
        try:
            client.connect(broker, port, 60)
            client.loop_start()  # Non-blocking loop for publishing
            self.stdout.write(self.style.SUCCESS(f"Connected to MQTT broker at {broker}:{port} for health tracking"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to connect MQTT client: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("Starting Device Health Monitor (10s sweep)"))
        
        try:
            while True:
                now = timezone.now()
                thirty_sec_ago = now - timedelta(seconds=30)
                forty_five_sec_ago = now - timedelta(seconds=45)

                # 1. Ping devices that missed heartbeats for 30 seconds
                pending_ping = Device.objects.filter(
                    connection_status=Device.CONNECTION_CONNECTED,
                    last_heartbeat_at__lt=thirty_sec_ago,
                    last_heartbeat_at__gte=forty_five_sec_ago
                )
                
                for device in pending_ping:
                    ping_topic = f"device/{device.device_id}/ping/status_query"
                    client.publish(ping_topic, "{}")
                    self.stdout.write(f"Sent status query to {device.device_id}")

                # 2. Mark devices inactive if missing heartbeat > 45 seconds
                timed_out = Device.objects.filter(
                    connection_status=Device.CONNECTION_CONNECTED,
                    last_heartbeat_at__lt=forty_five_sec_ago
                )
                
                for device in timed_out:
                    device.connection_status = Device.CONNECTION_DISCONNECTED
                    device.save(update_fields=['connection_status'])
                    self.stdout.write(self.style.WARNING(f"Device {device.device_id} timed out. Marked OFFLINE."))
                    
                time.sleep(10)
        except KeyboardInterrupt:
            self.stdout.write("Shutting down health monitor...")
        finally:
            client.loop_stop()
            client.disconnect()

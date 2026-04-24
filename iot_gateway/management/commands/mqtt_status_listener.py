import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from devices.models import Device
from django.conf import settings

class Command(BaseCommand):
    help = 'Starts a background MQTT listener for device status updates'

    def handle(self, *args, **options):
        if not settings.MQTT_ENABLED:
            self.stdout.write(self.style.WARNING("MQTT is disabled"))
            return

        import paho.mqtt.client as mqtt

        broker = settings.MQTT_BROKER_URL
        port = settings.MQTT_BROKER_PORT
        
        self.stdout.write(self.style.SUCCESS(f"Starting MQTT Listener on {broker}:{port}"))
        
        # Use a proper client ID for the backend
        client = mqtt.Client(client_id="django_backend_listener", clean_session=True)
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        
        try:
            client.connect(broker, port, 60)
            client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write("Shutting down...")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"MQTT Connection Error: {e}"))

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.stdout.write(self.style.SUCCESS("Connected to MQTT Broker"))
            # Subscribe to all relevant device topics
            client.subscribe("device/+/heartbeat")
            client.subscribe("device/+/status")
            client.subscribe("device/+/disconnect")
            self.stdout.write("Subscribed to device/+/heartbeat, status, disconnect")
        else:
            self.stdout.write(self.style.ERROR(f"Connection failed with code {rc}"))

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = msg.payload.decode('utf-8').strip()
            
            # Pattern: device/<device_id>/<action>
            parts = topic.split('/')
            if len(parts) >= 3 and parts[0] == 'device':
                device_id = parts[1]
                action = parts[2]
                self.stdout.write(f"Incoming Update: {device_id} [{action}] -> {payload}")
                
                # Fetch device and update
                try:
                    device = Device.objects.get(device_id=device_id)
                    
                    if action == 'heartbeat' or action == 'status':
                        # Parse JSON payload if needed, or fallback to simple string
                        try:
                            data = json.loads(payload)
                            status_val = data.get('status', 'active')
                        except json.JSONDecodeError:
                            status_val = payload
                            
                        if status_val == "active":
                            device.connection_status = Device.CONNECTION_CONNECTED
                            device.last_heartbeat_at = timezone.now()
                            device.save(update_fields=['connection_status', 'last_heartbeat_at'])
                            self.stdout.write(self.style.SUCCESS(f"Status: {device_id} is now ONLINE"))
                        elif status_val in ["inactive", "offline"]:
                            device.connection_status = Device.CONNECTION_DISCONNECTED
                            device.save(update_fields=['connection_status'])
                            self.stdout.write(self.style.WARNING(f"Status: {device_id} is now OFFLINE"))
                            
                    elif action == 'disconnect':
                        device.connection_status = Device.CONNECTION_DISCONNECTED
                        device.save(update_fields=['connection_status'])
                        self.stdout.write(self.style.WARNING(f"Status: {device_id} explicitly DISCONNECTED"))
                        
                except Device.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Status Error: Device {device_id} not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing MQTT message: {e}"))

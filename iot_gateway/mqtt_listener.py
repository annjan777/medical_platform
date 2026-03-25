"""
Core MQTT listener logic — runs as a daemon thread automatically
when Django starts (via IotGatewayConfig.ready()).

This replaces the need to manually run:
  python3 manage.py mqtt_status_listener
"""
import os
import json
import logging
import threading
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

_listener_thread = None  # global ref so we only start once


def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("[MQTT] Connected to broker")
        client.subscribe("device/+/heartbeat")
        client.subscribe("device/+/status")
        client.subscribe("device/+/disconnect")
        client.subscribe("device/+/reading")
        logger.info("[MQTT] Subscribed to device/+/heartbeat,status,disconnect,reading")
    else:
        logger.error(f"[MQTT] Connection failed with code {rc}")


def _on_message(client, userdata, msg):
    """Process incoming MQTT messages and update Device.connection_status in DB."""
    from django.utils import timezone
    from devices.models import Device, DeviceReading
    from screening.models import ScreeningSession

    topic = msg.topic
    try:
        payload = msg.payload.decode('utf-8').strip()
        parts = topic.split('/')
        if len(parts) >= 3 and parts[0] == 'device':
            device_id = parts[1]
            action = parts[2]
            logger.info(f"[MQTT] {device_id} [{action}] -> {payload}")

            try:
                device = Device.objects.get(device_id=device_id)

                if action in ('heartbeat', 'status'):
                    try:
                        data = json.loads(payload)
                        status_val = data.get('status', 'active')
                    except (json.JSONDecodeError, ValueError):
                        status_val = payload

                    if status_val == 'active':
                        device.connection_status = Device.CONNECTION_CONNECTED
                        device.last_heartbeat_at = timezone.now()
                        device.save(update_fields=['connection_status', 'last_heartbeat_at'])
                        logger.info(f"[MQTT] {device_id} is now ONLINE")
                    elif status_val in ('inactive', 'offline'):
                        device.connection_status = Device.CONNECTION_DISCONNECTED
                        device.save(update_fields=['connection_status'])
                        logger.info(f"[MQTT] {device_id} is now OFFLINE")

                elif action == 'disconnect':
                    device.connection_status = Device.CONNECTION_DISCONNECTED
                    device.save(update_fields=['connection_status'])
                    logger.info(f"[MQTT] {device_id} explicitly DISCONNECTED")

                elif action == 'reading':
                    # New logic to handle MQTT based data ingestion
                    try:
                        data = json.loads(payload)
                        session_id = data.get('session_id')
                        reading_type = data.get('reading_type', 'vitals')
                        value = data.get('value')

                        if session_id and value:
                            session = ScreeningSession.objects.get(pk=session_id)
                            
                            # Create a DeviceReading record
                            DeviceReading.objects.create(
                                device=device,
                                patient=session.patient,
                                reading_type=reading_type,
                                reading_data={"value": value, "session_id": session_id, "source": "MQTT"},
                                recorded_at=timezone.now(),
                                recorded_by=session.conducted_by
                            )
                            logger.info(f"[MQTT] Created reading for session {session_id} from {device_id}")
                        else:
                            logger.warning(f"[MQTT] Missing session_id or value in reading payload: {payload}")
                    except Exception as e:
                        logger.error(f"[MQTT] Failed to process reading: {e}")

            except Device.DoesNotExist:
                logger.warning(f"[MQTT] Device not found: {device_id}")

    except Exception as e:
        logger.error(f"[MQTT] Error processing message on {topic}: {e}")


def _run_loop(broker, port):
    """Blocking MQTT loop — runs in a background daemon thread."""
    client = mqtt.Client(client_id="django_backend_listener", clean_session=True)
    client.on_connect = _on_connect
    client.on_message = _on_message

    try:
        client.connect(broker, port, keepalive=60)
        logger.info(f"[MQTT] Listener started on {broker}:{port}")
        client.loop_forever()
    except Exception as e:
        logger.error(f"[MQTT] Listener error: {e}")


def start_listener():
    """
    Start the MQTT listener in a daemon background thread.
    Safe to call multiple times — starts only once.
    """
    global _listener_thread
    if _listener_thread and _listener_thread.is_alive():
        return  # already running

    broker = os.environ.get('MQTT_BROKER_URL', 'localhost')
    port = int(os.environ.get('MQTT_BROKER_PORT', 1883))

    _listener_thread = threading.Thread(
        target=_run_loop,
        args=(broker, port),
        name="mqtt-status-listener",
        daemon=True,  # dies automatically when Django exits
    )
    _listener_thread.start()
    logger.info("[MQTT] Background listener thread started")

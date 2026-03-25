import json
import time
import requests
import paho.mqtt.client as mqtt
import argparse
from datetime import datetime

# Configuration
SERVER_URL = "http://localhost:8000"
MQTT_HOST = "localhost"
MQTT_PORT = 1883
DEFAULT_DEVICE_ID = "DEV-OX-001"
DEFAULT_SESSION_ID = 1

# ==============================================================================================
# MQTT TOPICS & PAYLOAD REFERENCE
# ==============================================================================================
MQTT_REFERENCE = {
    "device/{device_id}/heartbeat": {
        "direction": "DEVICE -> SERVER",
        "payload": {"status": "active"},
        "desc": "Keeps the device in 'CONNECTED' state in the dashboard."
    },
    "device/{device_id}/status": {
        "direction": "DEVICE -> SERVER",
        "payload": "active | inactive | offline",
        "desc": "Direct status updates (can be JSON or plain text)."
    },
    "device/{device_id}/disconnect": {
        "direction": "DEVICE -> SERVER",
        "payload": "offline",
        "desc": "Explicit disconnect signal to mark device as 'DISCONNECTED'."
    },
    "{device_id}/ping": {
        "direction": "SERVER -> DEVICE",
        "payload": "status",
        "desc": "Triggered by Health Assistant to check if device is reachable."
    },
    "{device_id}/{session_id}/{scan_type}": {
        "direction": "SERVER -> DEVICE",
        "payload": "patient_id: XXX patient_name: XXX patient_age: XX patient_gender: XXX",
        "desc": "Triggered by clicking 'Start Scan' in the dashboard. scan_type can be 'vitals', 'image', etc."
    }
}

# ==============================================================================================
# HTTP ENDPOINTS & PAYLOAD REFERENCE
# ==============================================================================================
HTTP_REFERENCE = [
    {
        "url": "/iot-gateway/receive-text/",
        "method": "POST",
        "payload": {
            "device_id": "string",
            "session_id": "int (optional for status)",
            "reading_type": "spO2 | heart_rate | blood_pressure",
            "value": "string"
        },
        "desc": "Main endpoint for ingesting text-based IoT data and vitals."
    },
    {
        "url": "/iot-gateway/receive-image/",
        "method": "POST (Multipart)",
        "payload": {
            "image": "FileObject",
            "device_id": "string",
            "session_id": "int"
        },
        "desc": "Endpoint for uploading medical scans/images directly."
    },
    {
        "url": "/iot-gateway/session/upload/init/",
        "method": "POST",
        "payload": {"device_id": "string", "session_token": "string"},
        "desc": "Gets a pre-signed S3 URL for large payload uploads (ZIP archives)."
    },
    {
        "url": "/iot-gateway/session/upload/done/",
        "method": "POST",
        "payload": {"object_name": "string", "device_id": "string", "session_id": "int"},
        "desc": "Notifies the server after an S3 upload is complete to finalize the session."
    }
]

# ==============================================================================================
# CORE LOGIC
# ==============================================================================================

def print_reference():
    print("\n" + "="*80)
    print(" MEDICAL PLATFORM: MQTT TOPIC INTERFACES")
    print("="*80)
    for topic, info in MQTT_REFERENCE.items():
        print(f"TOPIC: {topic}")
        print(f" DIR: {info['direction']}")
        print(f" DESC: {info['desc']}")
        print(f" PAYLOAD: {json.dumps(info['payload'], indent=2)}")
        print("-" * 40)

    print("\n" + "="*80)
    print(" MEDICAL PLATFORM: HTTP API INTERFACES")
    print("="*80)
    for api in HTTP_REFERENCE:
        print(f"URL: {SERVER_URL}{api['url']}")
        print(f" METHOD: {api['method']}")
        print(f" DESC: {api['desc']}")
        print(f" PAYLOAD: {json.dumps(api['payload'], indent=2)}")
        print("-" * 40)

def simulate_device(device_id):
    """Simple simulation to heart-beat and send a mock reading via MQTT and HTTP."""
    print(f"\n[SIMULATOR] Starting Device Simulation: {device_id}")
    
    # 1. MQTT Heartbeat
    client = mqtt.Client(client_id=f"sim_{device_id}")
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        topic = f"device/{device_id}/heartbeat"
        payload = json.dumps({"status": "active"})
        client.publish(topic, payload)
        print(f"[MQTT] -> Published Heartbeat on {topic}")
    except Exception as e:
        print(f"[MQTT] ! Failed to connect to broker: {e}")

    # 2. HTTP Data Reading
    print(f"[HTTP] -> Sending mock reading to {SERVER_URL}/iot-gateway/receive-text/")
    payload = {
        "device_id": device_id,
        "session_id": DEFAULT_SESSION_ID,
        "reading_type": "heart_rate",
        "value": "72 bpm"
    }
    try:
        r = requests.post(f"{SERVER_URL}/iot-gateway/receive-text/", json=payload)
        print(f"[HTTP] <- Received Status {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[HTTP] ! Failed to connect to server: {e}")

def monitor_traffic():
    """Subscribes to all device topics and logs incoming messages."""
    print(f"\n[MONITOR] Listening for MQTT traffic on {MQTT_HOST}:{MQTT_PORT}...")
    print("[MONITOR] Topics: device/+/heartbeat, device/+/status, device/+/disconnect, +/+, +/+/+")

    def on_connect(client, userdata, flags, rc):
        client.subscribe("device/+/heartbeat")
        client.subscribe("device/+/status")
        client.subscribe("device/+/disconnect")
        client.subscribe("+/ping")
        client.subscribe("+/+/+")
        print("[MONITOR] Subscription Active.")

    def on_message(client, userdata, msg):
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Topic: {msg.topic}")
        try:
            print(f"       Payload: {msg.payload.decode('utf-8')}")
        except:
            print(f"       Payload: [Binary Data]")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[MONITOR] Stopping monitoring...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Medical IoT Communication Interface & Testing Script")
    parser.add_argument("--ref", action="store_true", help="Print the MQTT and HTTP Interface Reference")
    parser.add_argument("--simulate", action="store_true", help="Simulate a device check-in (Heartbeat + Mock Reading)")
    parser.add_argument("--monitor", action="store_true", help="Monitor all MQTT traffic")
    parser.add_argument("--device", type=str, default=DEFAULT_DEVICE_ID, help="Device ID to use for simulation")
    
    args = parser.parse_args()
    
    if args.ref:
        print_reference()
    elif args.simulate:
        simulate_device(args.device)
    elif args.monitor:
        monitor_traffic()
    else:
        parser.print_help()
        print("\nTIP: Run with '--ref' to see all communication patterns.")

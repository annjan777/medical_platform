import json
import os
import boto3
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.db import transaction
import requests

from screening.models import ScreeningSession, ScreeningAttachment
from devices.models import Device, DeviceReading
from patients.models import Patient

@csrf_exempt
def receive_text_data(request):
    """
    Endpoint to receive text data (e.g., from an MQTT bridge).
    Expected data: {
        "device_id": "...",
        "session_id": "...",
        "reading_type": "...",
        "value": "..."
    }
    """
    if request.method == 'POST':
        try:
            # Handle both JSON and Form-Data (CURL -F)
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            device_id = data.get('device_id')
            session_id = data.get('session_id')
            reading_type = data.get('reading_type', 'vitals')
            value = data.get('value')

            if not device_id:
                return JsonResponse({"status": "error", "message": "device_id required"}, status=400)

            device = get_object_or_404(Device, device_id=device_id)
            
            # If it's just a status ping ("active" or "inactive")
            if value in ["active", "inactive", "offline"]:
                device.connection_status = Device.CONNECTION_CONNECTED if value == "active" else Device.CONNECTION_DISCONNECTED
                device.last_heartbeat_at = timezone.now()
                device.save()
                status_msg = "active" if value == "active" else "inactive"
                return JsonResponse({"status": "success", "message": f"Device marked as {status_msg}"})

            # Otherwise, it's a reading that requires a session
            if not session_id:
                return JsonResponse({"status": "error", "message": "session_id required for data readings"}, status=400)
                
            session = get_object_or_404(ScreeningSession, pk=session_id)
            
            # Create a DeviceReading
            DeviceReading.objects.create(
                device=device,
                patient=session.patient,
                reading_type=reading_type,
                reading_data={"value": value, "session_id": session_id},
                recorded_at=timezone.now(),
                recorded_by=session.conducted_by
            )

            # Update device state (Heartbeat)
            device.last_heartbeat_at = timezone.now()
            device.connection_status = Device.CONNECTION_CONNECTED
            device.save()

            return JsonResponse({"status": "success", "message": "Reading recorded successfully"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return HttpResponse("Endpoint for IoT text data receiver")

@csrf_exempt
def receive_image_data(request):
    """
    Endpoint to receive scans/images via HTTP POST.
    Expected: Multipart form with 'image', 'device_id', 'session_id'
    """
    if request.method == 'POST':
        try:
            device_id = request.POST.get('device_id')
            session_id = request.POST.get('session_id')
            image_file = request.FILES.get('image')

            if not image_file:
                return JsonResponse({"status": "error", "message": "No image provided"}, status=400)

            device = get_object_or_404(Device, device_id=device_id)
            session = get_object_or_404(ScreeningSession, pk=session_id)

            # Determine file type
            import mimetypes
            content_type = mimetypes.guess_type(image_file.name)[0] or 'image/jpeg'

            # Save as a ScreeningAttachment
            attachment = ScreeningAttachment.objects.create(
                session=session,
                file=image_file,
                file_type=content_type,
                description=f"IoT Data Upload from {device.name}",
                uploaded_by=session.conducted_by
            )

            # Update device state (Heartbeat)
            device.last_heartbeat_at = timezone.now()
            device.connection_status = Device.CONNECTION_CONNECTED
            device.save()

            return JsonResponse({"status": "success", "attachment_id": attachment.id})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return HttpResponse("Endpoint for IoT image data receiver")

def get_server_info(request):
    """
    Helper endpoint for IoT devices to discover server IP/URL.
    In AWS, this might be useful for devices to dynamic-configure their MQTT/HTTP targets.
    """
    # Attempt to get public IP or use hostname
    server_ip = request.META.get('HTTP_HOST', 'localhost')
    
    # In a real AWS env, you might fetch this via IMDS or env vars
    public_ip = os.environ.get('SERVER_PUBLIC_IP', server_ip)

    return JsonResponse({
        "server_time": timezone.now().isoformat(),
        "public_ip": public_ip,
        "mqtt_broker": os.environ.get('MQTT_BROKER_URL', 'localhost'),
        "endpoints": {
            "text": request.build_absolute_uri('/iot/receive-text/'),
            "image": request.build_absolute_uri('/iot/receive-image/')
        }
    })

import paho.mqtt.publish as publish

@csrf_exempt
def trigger_scan(request, session_id):
    """
    Endpoint to trigger a scan on an IoT device via MQTT.
    Expected data: { "scan_type": "vitals" | "image" | "ecg" ... }
    MQTT Topic: {device_id}/{session_id}/{scan_type}
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    
    try:
        session = get_object_or_404(ScreeningSession, pk=session_id)
        device = session.device_used
        
        if not device:
            return JsonResponse({"status": "error", "message": "No device associated with this session"}, status=400)
        
        data = json.loads(request.body) if request.body else {}
        scan_type = data.get('scan_type', 'vitals')
        
        # Build message payload
        p = session.patient
        patient_info = f"patient_id: {p.patient_id or p.id} " \
                       f"patient_name: {p.first_name} {p.last_name} " \
                       f"patient_age: {p.age} " \
                       f"patient_gender: {p.get_gender_display()} patient"
        
        # MQTT Topic: device_id/session_id/scan_type
        topic = f"{device.device_id}/{session.id}/{scan_type}"
        
        # MQTT Broker settings
        broker = os.environ.get('MQTT_BROKER_URL', 'localhost')
        port = int(os.environ.get('MQTT_BROKER_PORT', 1883))
        
        # Publish message
        publish.single(topic, payload=patient_info, hostname=broker, port=port)
        
        return JsonResponse({
            "status": "success",
            "message": f"Scan trigger sent to {device.name}",
            "topic": topic,
            "payload": patient_info
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def ping_device(request, device_id):
    """
    Triggers a status request to a specific device.
    Topic: {device_id}/ping
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
        
    try:
        device = get_object_or_404(Device, pk=device_id)
        topic = f"{device.device_id}/ping"
        
        # Publish request
        broker = os.environ.get('MQTT_BROKER_URL', 'localhost')
        port = int(os.environ.get('MQTT_BROKER_PORT', 1883))
        publish.single(topic, payload="status", hostname=broker, port=port)
        
        return JsonResponse({"status": "success", "message": f"Ping sent to {device.name}"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

def check_session_data(request, session_id):
    """
    Polling endpoint for the frontend to check if new data has arrived for a session.
    """
    session = get_object_or_404(ScreeningSession, pk=session_id)
    
    # Get recent readings
    readings = DeviceReading.objects.filter(
        patient=session.patient,
        recorded_at__gte=session.created_at
    ).order_by('-recorded_at')[:5]
    
    # Get recent attachments
    attachments = ScreeningAttachment.objects.filter(
        session=session
    ).order_by('-created_at')[:5]
    
    readings_data = [{
        "id": r.id,
        "type": r.reading_type,
        "data": r.reading_data,
        "time": r.recorded_at.isoformat()
    } for r in readings]
    
    attachments_data = [{
        "id": a.id,
        "url": a.file.url if a.file else None,
        "desc": a.description,
        "time": a.created_at.isoformat()
    } for a in attachments]
    
    # Returning the data
    return JsonResponse({
        'status': 'success',
        'readings': readings_data,
        'attachments': attachments_data,
        'count': readings.count() + attachments.count()
    })

# ==========================================
# PHASE 3: Device Assignment & S3 Upload API
# ==========================================

@csrf_exempt
@transaction.atomic
def assign_device(request, device_id):
    """Locks a device for the currently authenticated Health Assistant."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Needs auth check here ideally, but using stub handling
    ha_user = request.user if request.user.is_authenticated else None
    
    try:
        # Use simple get, lock row with select_for_update to avoid race conditions
        device = Device.objects.select_for_update().get(id=device_id)
        
        if device.status != Device.STATUS_ACTIVE:
            return JsonResponse({'error': 'Device is not active'}, status=400)
            
        if device.assigned_to is not None and device.assigned_to != ha_user:
            return JsonResponse({'error': 'Device is already locked by another user'}, status=409)
            
        device.assigned_to = ha_user
        device.assigned_at = timezone.now()
        device.save()
        
        return JsonResponse({'status': 'success', 'message': f'Device {device_id} assigned'})
    except Device.DoesNotExist:
        return JsonResponse({'error': 'Device not found'}, status=404)

@csrf_exempt
def release_device(request, device_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        device = Device.objects.get(id=device_id)
        device.assigned_to = None
        device.assigned_at = None
        device.save()
        return JsonResponse({'status': 'success', 'message': f'Device {device_id} released'})
    except Device.DoesNotExist:
        return JsonResponse({'error': 'Device not found'}, status=404)

@csrf_exempt
def upload_init(request):
    """Generates a Presigned PUT URL for the device to upload ZIPs directly to S3."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        session_token = data.get('session_token') # Example auth
        
        if not device_id:
            return JsonResponse({'error': 'device_id required'}, status=400)
            
        # Example S3 setup
        from botocore.client import Config
        s3_client_kwargs = {
            'aws_access_key_id': getattr(settings, 'AWS_ACCESS_KEY_ID', 'dummy'),
            'aws_secret_access_key': getattr(settings, 'AWS_SECRET_ACCESS_KEY', 'dummy'),
            'region_name': getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
            'config': Config(signature_version='s3v4')
        }
        if getattr(settings, 'AWS_S3_ENDPOINT_URL', None):
            s3_client_kwargs['endpoint_url'] = settings.AWS_S3_ENDPOINT_URL
            
        s3_client = boto3.client('s3', **s3_client_kwargs)
        
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME')
        object_name = f"uploads/{device_id}/{session_token}_{timezone.now().timestamp()}.zip"
        
        # Using presigned POST is strictly more robust against python SignatureDoesNotMatch errors than presigned PUT
        presigned_data = s3_client.generate_presigned_post(
            Bucket=bucket_name,
            Key=object_name,
            ExpiresIn=3600
        )
        
        return JsonResponse({
            'status': 'success',
            'upload_url': presigned_data['url'],
            'upload_fields': presigned_data['fields'],
            'object_name': object_name
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def upload_done(request):
    """Called by device when S3 upload is complete."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        object_name = data.get('object_name')
        device_id = data.get('device_id')
        session_id = data.get('session_id')
        
        if not object_name or not session_id:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
            
        session = ScreeningSession.objects.filter(id=session_id).first()
        if session:
            # Bypass Celery Extraction and directly attach the S3 ZIP to the ScreeningSession attachments!
            from screening.models import ScreeningAttachment
            ScreeningAttachment.objects.create(
                session=session,
                file=object_name,  # Saves the S3 Object Key in the FileField
                file_type='application/zip',
                description=f"Raw IoT Device Payload (ZIP) from {device_id}",
                uploaded_by=None
            )
            
            # Updating upload status since extraction is skipped
            session.upload_status = 'uploaded'
            session.save()
            
        return JsonResponse({'status': 'success', 'message': 'Upload Finalized! ZIP archive attached to Session successfully.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

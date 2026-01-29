from django.utils import timezone
from .models import AuditLog


def log_action(user, action, model_name, object_id=None, object_repr="", changes=None, ip_address=None):
    """
    Log an action to the audit trail.
    
    Args:
        user: The user who performed the action
        action: The action type (create, update, delete, login, logout, access)
        model_name: The name of the model that was acted upon
        object_id: The ID of the object (optional)
        object_repr: String representation of the object
        changes: Dictionary of changes made (for update actions)
        ip_address: IP address of the user (optional)
    """
    AuditLog.objects.create(
        user=user,
        action=action,
        model=model_name,
        object_id=object_id,
        object_repr=object_repr,
        changes=changes,
        ip_address=ip_address,
        timestamp=timezone.now()
    )


def log_model_change(user, instance, action, changes=None, ip_address=None):
    """
    Log a model change (create, update, delete).
    
    Args:
        user: The user who performed the action
        instance: The model instance that was changed
        action: The action type (create, update, delete)
        changes: Dictionary of changes made (for update actions)
        ip_address: IP address of the user (optional)
    """
    model_name = instance.__class__.__name__
    object_id = instance.pk
    object_repr = str(instance)
    
    log_action(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        object_repr=object_repr,
        changes=changes,
        ip_address=ip_address
    )


def get_client_ip(request):
    """
    Get the client IP address from the request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

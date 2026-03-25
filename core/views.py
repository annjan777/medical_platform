from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def session_ping(request):
    # SESSION_SAVE_EVERY_REQUEST = True will automatically reset the session age here
    return JsonResponse({'status': 'active'})

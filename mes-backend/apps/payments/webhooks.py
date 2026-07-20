import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.payments import services


@csrf_exempt
@require_POST
def snippe_webhook(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event_id = payload.get("event_id", "")
    result = services.handle_webhook(event_id, payload)
    return HttpResponse(status=200)

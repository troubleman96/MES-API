import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.payments import services
from apps.payments.clients import SnippeClient


@csrf_exempt
@require_POST
def snippe_webhook(request):
    timestamp = request.headers.get("X-Webhook-Timestamp", "")
    signature = request.headers.get("X-Webhook-Signature", "")

    if not timestamp or not signature:
        return HttpResponse(status=401)

    client = SnippeClient()
    if not client.verify_webhook_signature(request.body, timestamp, signature):
        return HttpResponse(status=401)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event_id = payload.get("id", "")
    if not event_id:
        return HttpResponse(status=400)

    services.handle_webhook(event_id, payload)
    return HttpResponse(status=200)

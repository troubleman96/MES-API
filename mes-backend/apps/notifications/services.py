from django.conf import settings
from django.utils import timezone
from rest_framework import status

from apps.core.responses import envelope_error, envelope_ok
from apps.notifications.clients import SendAfricaClient
from apps.notifications.models import DeviceToken, Notification
from apps.notifications.serializers import NotificationSerializer


def notify(event_type: str, account, context: dict):
    title = context.get("title", "MES Notification")
    body = context.get("body", "")

    notification = Notification.objects.create(
        account=account,
        type=event_type,
        title=title,
        body=body,
    )

    _send_fcm(account, title, body)

    sms_event_types = ["order_confirmed", "payment_received", "return_due"]
    if event_type in sms_event_types and account.phone:
        client = SendAfricaClient()
        client.send_sms(account.phone, body)

    return notification


def _send_fcm(account, title, body):
    tokens = DeviceToken.objects.filter(account=account)
    if not tokens.exists():
        return

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_JSON)
            firebase_admin.initialize_app(cred)

        registration_ids = list(tokens.values_list("fcm_token", flat=True))
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            tokens=registration_ids,
        )
        messaging.send_each_for_multicast(message)
    except Exception:
        pass


def list_notifications(user):
    notifications = Notification.objects.filter(account=user)
    return envelope_ok(data=NotificationSerializer(notifications, many=True).data)


def unread_count(user):
    count = Notification.objects.filter(account=user, read_at__isnull=True).count()
    return envelope_ok(data={"count": count})


def mark_read(user, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, account=user)
    except Notification.DoesNotExist:
        return envelope_error("not_found", "Notification not found.", status=status.HTTP_404_NOT_FOUND)

    if not notification.read_at:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])

    return envelope_ok(data=NotificationSerializer(notification).data)


def mark_all_read(user):
    Notification.objects.filter(account=user, read_at__isnull=True).update(read_at=timezone.now())
    return envelope_ok(data={"message": "All notifications marked as read."})


def register_device(user, fcm_token):
    device, created = DeviceToken.objects.get_or_create(
        account=user,
        fcm_token=fcm_token,
    )
    return envelope_ok(
        data={"message": "Device registered.", "id": str(device.id)},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )

import uuid

from django.db import models


class Notification(models.Model):
    TYPE_CHOICES = [
        ("order_confirmed", "Order Confirmed"),
        ("payment_received", "Payment Received"),
        ("return_due", "Return Due"),
        ("merchant_message", "Merchant Message"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(choices=TYPE_CHOICES, max_length=20)
    title = models.CharField(max_length=255)
    body = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]


class DeviceToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="device_tokens")
    fcm_token = models.CharField(max_length=255, unique=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "device_tokens"

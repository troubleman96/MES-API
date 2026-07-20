import uuid

from django.db import models


class PaymentIntent(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.OneToOneField("bookings.SubOrder", on_delete=models.CASCADE, related_name="payment")
    snippe_reference = models.CharField(max_length=64, unique=True)
    status = models.CharField(choices=STATUS_CHOICES, default="pending", max_length=15)
    amount_tzs = models.PositiveIntegerField()
    network = models.CharField(max_length=20, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payment_intents"


class WebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=20)
    event_id = models.CharField(max_length=64)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "webhook_events"
        unique_together = ["provider", "event_id"]

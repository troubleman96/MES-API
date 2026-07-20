from rest_framework import serializers

from apps.payments.models import PaymentIntent, WebhookEvent


class PaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = [
            "id", "sub_order", "snippe_reference", "status",
            "amount_tzs", "network", "failure_reason", "expires_at", "created_at",
        ]


class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = ["id", "provider", "event_id", "received_at"]

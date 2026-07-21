import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import status

from apps.bookings.models import SubOrder
from apps.core.responses import envelope_error, envelope_ok
from apps.payments.clients import SnippeClient
from apps.payments.models import PaymentIntent, WebhookEvent
from apps.payments.serializers import PaymentIntentSerializer


def create_payment(user, sub_order_id):
    try:
        sub_order = SubOrder.objects.select_related("order_group__buyer").get(id=sub_order_id)
    except SubOrder.DoesNotExist:
        return envelope_error("not_found", "Order not found.", status=status.HTTP_404_NOT_FOUND)

    if sub_order.order_group.buyer_id != user.id:
        return envelope_error("forbidden", "Access denied.", status=status.HTTP_403_FORBIDDEN)

    if sub_order.status != "pending_payment":
        return envelope_error("invalid_status", "Order is not awaiting payment.", status=status.HTTP_400_BAD_REQUEST)

    existing = PaymentIntent.objects.filter(sub_order=sub_order, status="pending").first()
    if existing:
        return envelope_ok(data=PaymentIntentSerializer(existing).data)

    client = SnippeClient()
    try:
        result = client.initiate_payment(
            amount_tzs=sub_order.subtotal_tzs,
            phone=user.phone or "",
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            email=user.email or "",
            description=f"MES Order {str(sub_order.id)[:8]}",
        )
    except Exception as e:
        return envelope_error("payment_gateway_error", str(e), status=status.HTTP_502_BAD_GATEWAY)

    payment = PaymentIntent.objects.create(
        sub_order=sub_order,
        snippe_reference=result.get("reference", str(uuid.uuid4())),
        amount_tzs=sub_order.subtotal_tzs,
        network=result.get("channel", {}).get("provider", "") if isinstance(result.get("channel"), dict) else "",
        expires_at=timezone.now() + timedelta(hours=4),
    )

    return envelope_ok(data=PaymentIntentSerializer(payment).data, status=status.HTTP_201_CREATED)


def get_payment_status(user, sub_order_id):
    try:
        sub_order = SubOrder.objects.get(id=sub_order_id)
    except SubOrder.DoesNotExist:
        return envelope_error("not_found", "Order not found.", status=status.HTTP_404_NOT_FOUND)

    if sub_order.order_group.buyer_id != user.id and sub_order.merchant_id != user.id:
        return envelope_error("forbidden", "Access denied.", status=status.HTTP_403_FORBIDDEN)

    payment = PaymentIntent.objects.filter(sub_order=sub_order).order_by("-created_at").first()
    if not payment:
        return envelope_error("not_found", "No payment found for this order.", status=status.HTTP_404_NOT_FOUND)

    return envelope_ok(data=PaymentIntentSerializer(payment).data)


def handle_webhook(event_id: str, payload: dict):
    if WebhookEvent.objects.filter(provider="snippe", event_id=event_id).exists():
        return envelope_ok(data={"message": "Event already processed."})

    with transaction.atomic():
        WebhookEvent.objects.create(provider="snippe", event_id=event_id)

        event_type = payload.get("type", "")
        data = payload.get("data", {})
        reference = data.get("reference", "")

        if not reference:
            return envelope_error("invalid_payload", "Missing reference.", status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = PaymentIntent.objects.select_related("sub_order").get(snippe_reference=reference)
        except PaymentIntent.DoesNotExist:
            return envelope_error("not_found", "Payment intent not found.", status=status.HTTP_404_NOT_FOUND)

        if event_type == "payment.completed":
            payment.status = "completed"
            channel = data.get("channel", {})
            payment.network = channel.get("provider", payment.network) if isinstance(channel, dict) else payment.network
            payment.save(update_fields=["status", "network"])

            payment.sub_order.status = "confirmed"
            payment.sub_order.save(update_fields=["status"])

            from apps.contracts.services import generate_contract_pdf
            generate_contract_pdf(payment.sub_order)

        elif event_type == "payment.failed":
            payment.status = "failed"
            payment.failure_reason = data.get("failure_reason", "")
            payment.save(update_fields=["status", "failure_reason"])

            payment.sub_order.status = "payment_failed"
            payment.sub_order.save(update_fields=["status"])

        elif event_type == "payment.expired":
            payment.status = "expired"
            payment.save(update_fields=["status"])

            payment.sub_order.status = "payment_failed"
            payment.sub_order.save(update_fields=["status"])

    return envelope_ok(data={"message": "Webhook processed."})

import io

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from rest_framework import status

from apps.bookings.models import SubOrder
from apps.contracts.models import Contract, Signature
from apps.contracts.serializers import ContractDetailSerializer
from apps.core.responses import envelope_error, envelope_ok


def generate_contract_pdf(sub_order):
    contract, _ = Contract.objects.get_or_create(
        sub_order=sub_order,
        defaults={"pdf_url": ""},
    )

    if contract.pdf_url:
        return contract

    lines = sub_order.lines.all()
    buyer = sub_order.order_group.buyer

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, height - 3 * cm, "Medical Equipment Rental Agreement")

    c.setFont("Helvetica", 10)
    y = height - 5 * cm
    c.drawString(2 * cm, y, f"Contract Reference: MES-{str(sub_order.id)[:8]}")
    y -= 0.5 * cm
    c.drawString(2 * cm, y, f"Date: {timezone.now().strftime('%Y-%m-%d')}")
    y -= 1 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Buyer Information")
    y -= 0.5 * cm
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, y, f"Name: {buyer.first_name} {buyer.last_name}")
    y -= 0.5 * cm
    c.drawString(2 * cm, y, f"Facility: {buyer.facility_name}")
    y -= 0.5 * cm
    c.drawString(2 * cm, y, f"Email: {buyer.email}")
    y -= 1 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Rental Items")
    y -= 0.5 * cm
    c.setFont("Helvetica", 10)

    for line in lines:
        c.drawString(2 * cm, y, f"• {line.product_name_snapshot} x{line.quantity} — TZS {line.daily_rate_snapshot_tzs}/day")
        y -= 0.4 * cm
        c.drawString(2.5 * cm, y, f"Period: {line.rental_start} to {line.rental_end}")
        y -= 0.4 * cm
        c.drawString(2.5 * cm, y, f"Line Total: TZS {line.line_total_tzs}")
        y -= 0.8 * cm

    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, f"Total Amount: TZS {sub_order.subtotal_tzs}")
    y -= 1 * cm

    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, y, "By signing this agreement, both parties agree to the terms of rental.")
    y -= 1 * cm
    c.drawString(2 * cm, y, "Signatures:")
    y -= 1.5 * cm
    c.drawString(2 * cm, y, "Buyer: ________________________")
    c.drawString(12 * cm, y, "Merchant: ________________________")

    c.save()
    buffer.seek(0)

    contract.pdf_url = f"contracts/{sub_order.id}/agreement.pdf"
    contract.save(update_fields=["pdf_url"])

    return contract


def get_contract(user, sub_order_id):
    try:
        sub_order = SubOrder.objects.get(id=sub_order_id)
    except SubOrder.DoesNotExist:
        return envelope_error("not_found", "Order not found.", status=status.HTTP_404_NOT_FOUND)

    if user.role == "buyer" and sub_order.order_group.buyer_id != user.id:
        return envelope_error("forbidden", "Access denied.", status=status.HTTP_403_FORBIDDEN)
    if user.role == "merchant" and sub_order.merchant_id != user.id:
        return envelope_error("forbidden", "Access denied.", status=status.HTTP_403_FORBIDDEN)

    contract = Contract.objects.filter(sub_order=sub_order).first()
    if not contract:
        return envelope_error("not_found", "Contract not found.", status=status.HTTP_404_NOT_FOUND)

    return envelope_ok(data=ContractDetailSerializer(contract).data)


def sign_contract(user, sub_order_id, data):
    if user.role != "buyer":
        return envelope_error("forbidden", "Only the buyer can sign the contract.", status=status.HTTP_403_FORBIDDEN)

    try:
        sub_order = SubOrder.objects.get(id=sub_order_id)
    except SubOrder.DoesNotExist:
        return envelope_error("not_found", "Order not found.", status=status.HTTP_404_NOT_FOUND)

    if sub_order.order_group.buyer_id != user.id:
        return envelope_error("forbidden", "Access denied.", status=status.HTTP_403_FORBIDDEN)

    contract = Contract.objects.filter(sub_order=sub_order).first()
    if not contract:
        return envelope_error("not_found", "Contract not found. It will be generated upon payment confirmation.", status=status.HTTP_404_NOT_FOUND)

    already_signed = Signature.objects.filter(contract=contract, signer=user).exists()
    if already_signed:
        return envelope_error("already_signed", "You have already signed this contract.", status=status.HTTP_400_BAD_REQUEST)

    signature = Signature.objects.create(
        contract=contract,
        signer=user,
        signature_image_url=data["signature_image_url"],
    )

    return envelope_ok(data={
        "message": "Contract signed successfully.",
        "signature_id": str(signature.id),
    }, status=status.HTTP_201_CREATED)

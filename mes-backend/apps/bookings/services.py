from datetime import date
from itertools import groupby
from operator import attrgetter

from django.db import transaction
from django.db.models import Q
from rest_framework import status

from apps.addresses.models import Address
from apps.bookings.models import OrderGroup, SubOrder, SubOrderLine
from apps.bookings.serializers import (
    OrderGroupSerializer,
    SubOrderListSerializer,
    SubOrderSerializer,
)
from apps.cart.models import CartLine
from apps.core.responses import envelope_error, envelope_ok
from apps.equipment.models import AvailabilityBlock, Product


def checkout(user, data):
    delivery_address_id = data.get("delivery_address_id")
    billing_address_id = data.get("billing_address_id")
    notes = data.get("notes", "")

    if not user.phone_verified:
        return envelope_error("phone_not_verified", "Phone verification required for checkout.", status=status.HTTP_403_FORBIDDEN)

    try:
        delivery_address = Address.objects.get(id=delivery_address_id, account=user)
        billing_address = Address.objects.get(id=billing_address_id, account=user)
    except Address.DoesNotExist:
        return envelope_error("invalid_address", "Invalid address.", status=status.HTTP_400_BAD_REQUEST)

    try:
        cart = user.cart
        cart_lines = list(cart.lines.select_related("product").all())
    except Exception:
        return envelope_error("empty_cart", "Cart is empty.", status=status.HTTP_400_BAD_REQUEST)

    if not cart_lines:
        return envelope_error("empty_cart", "Cart is empty.", status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        for line in cart_lines:
            product = line.product
            if not product.is_active:
                return envelope_error("cart_changed", f"{product.name} is no longer available.", status=status.HTTP_409_CONFLICT)

            has_conflict = AvailabilityBlock.objects.select_for_update().filter(
                product=product,
                start_date__lte=line.rental_end,
                end_date__gte=line.rental_start,
            ).exists()
            if has_conflict:
                return envelope_error("cart_changed", f"{product.name} is no longer available for selected dates.", status=status.HTTP_409_CONFLICT)

        order_group = OrderGroup.objects.create(
            buyer=user,
            delivery_address=delivery_address,
            billing_address=billing_address,
        )

        sorted_lines = sorted(cart_lines, key=attrgetter("product.merchant_id"))
        sub_orders_created = []

        for merchant_id, group in groupby(sorted_lines, key=attrgetter("product.merchant_id")):
            group_lines = list(group)
            subtotal = 0

            sub_order = SubOrder.objects.create(
                order_group=order_group,
                merchant_id=merchant_id,
                special_instructions=notes,
                subtotal_tzs=0,
            )

            for line in group_lines:
                days = (line.rental_end - line.rental_start).days
                line_total = line.product.daily_rate_tzs * days * line.quantity
                subtotal += line_total

                SubOrderLine.objects.create(
                    sub_order=sub_order,
                    product=line.product,
                    product_name_snapshot=line.product.name,
                    daily_rate_snapshot_tzs=line.product.daily_rate_tzs,
                    rental_start=line.rental_start,
                    rental_end=line.rental_end,
                    quantity=line.quantity,
                    line_total_tzs=line_total,
                )

                AvailabilityBlock.objects.create(
                    product=line.product,
                    start_date=line.rental_start,
                    end_date=line.rental_end,
                    reason="booked",
                    sub_order=sub_order,
                )

            sub_order.subtotal_tzs = subtotal
            sub_order.save(update_fields=["subtotal_tzs"])

            sub_orders_created.append({
                "id": str(sub_order.id),
                "merchant_name": sub_order.merchant.business_name,
                "subtotal_tzs": subtotal,
                "status": sub_order.status,
            })

        CartLine.objects.filter(cart=cart).delete()

    return envelope_ok(data={
        "order_group_id": str(order_group.id),
        "sub_orders": sub_orders_created,
    }, status=status.HTTP_201_CREATED)


def list_orders(user, query_params):
    qs = SubOrder.objects.select_related("merchant", "order_group")

    if user.role == "buyer":
        qs = qs.filter(order_group__buyer=user)
    else:
        qs = qs.filter(merchant=user)

    status_filter = query_params.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)

    return envelope_ok(data=SubOrderListSerializer(qs, many=True).data)


def get_order(user, sub_order_id):
    try:
        sub_order = SubOrder.objects.select_related("merchant", "order_group__buyer").prefetch_related("lines").get(id=sub_order_id)
    except SubOrder.DoesNotExist:
        return envelope_error("not_found", "Order not found.", status=status.HTTP_404_NOT_FOUND)

    if user.role == "buyer" and sub_order.order_group.buyer_id != user.id:
        return envelope_error("forbidden", "Access denied.", status=status.HTTP_403_FORBIDDEN)
    if user.role == "merchant" and sub_order.merchant_id != user.id:
        return envelope_error("forbidden", "Access denied.", status=status.HTTP_403_FORBIDDEN)

    return envelope_ok(data=SubOrderSerializer(sub_order).data)


def update_order_status(user, sub_order_id, new_status):
    try:
        sub_order = SubOrder.objects.get(id=sub_order_id, merchant=user)
    except SubOrder.DoesNotExist:
        return envelope_error("not_found", "Order not found.", status=status.HTTP_404_NOT_FOUND)

    allowed_transitions = {
        "pending_payment": ["confirmed", "cancelled"],
        "confirmed": ["dispatched"],
        "dispatched": ["delivered"],
        "delivered": ["return_due", "returned"],
        "return_due": ["returned"],
    }

    valid_next = allowed_transitions.get(sub_order.status, [])
    if new_status not in valid_next:
        return envelope_error("invalid_transition", f"Cannot transition from {sub_order.status} to {new_status}.", status=status.HTTP_400_BAD_REQUEST)

    if new_status == "dispatched":
        from apps.contracts.models import Contract, Signature
        has_contract = Contract.objects.filter(sub_order=sub_order).exists()
        has_signature = Signature.objects.filter(contract__sub_order=sub_order).exists()
        if not has_contract or not has_signature:
            return envelope_error("unsigned_contract", "Cannot dispatch without a signed contract.", status=status.HTTP_400_BAD_REQUEST)

    sub_order.status = new_status
    sub_order.save(update_fields=["status"])

    return envelope_ok(data=SubOrderSerializer(sub_order).data)

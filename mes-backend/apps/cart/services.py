from datetime import date

from django.db import transaction
from rest_framework import status

from apps.cart.models import Cart, CartLine
from apps.cart.serializers import CartLineSerializer, CartSerializer
from apps.core.responses import envelope_error, envelope_ok
from apps.equipment.models import AvailabilityBlock, Product


def get_cart(user):
    cart, _ = Cart.objects.get_or_create(account=user)
    return envelope_ok(data=CartSerializer(cart).data)


def replace_cart(user, lines_data):
    cart, _ = Cart.objects.get_or_create(account=user)

    with transaction.atomic():
        stale_lines = []

        CartLine.objects.filter(cart=cart).delete()

        for line_data in lines_data:
            product = line_data["product"]
            if isinstance(product, str):
                try:
                    product = Product.objects.get(id=product, is_active=True)
                except Product.DoesNotExist:
                    stale_lines.append({
                        "product": line_data["product"],
                        "reason": "product_not_found",
                    })
                    continue
            elif not product.is_active:
                stale_lines.append({
                    "product": str(product.id),
                    "reason": "product_not_found",
                })
                continue

            if line_data["rental_start"] >= line_data["rental_end"]:
                stale_lines.append({
                    "product": str(product.id),
                    "reason": "invalid_dates",
                })
                continue

            has_conflict = AvailabilityBlock.objects.filter(
                product=product,
                start_date__lte=line_data["rental_end"],
                end_date__gte=line_data["rental_start"],
            ).exists()
            if has_conflict:
                stale_lines.append({
                    "product": str(product.id),
                    "product_name": product.name,
                    "reason": "unavailable",
                })
                continue

            if product.daily_rate_tzs != line_data.get("daily_rate_tzs", product.daily_rate_tzs):
                stale_lines.append({
                    "product": str(product.id),
                    "product_name": product.name,
                    "reason": "price_changed",
                    "current_price": product.daily_rate_tzs,
                })
                continue

            CartLine.objects.create(
                cart=cart,
                product=product,
                rental_start=line_data["rental_start"],
                rental_end=line_data["rental_end"],
                quantity=line_data.get("quantity", 1),
                added_at=line_data.get("added_at", date.today()),
            )

    cart = Cart.objects.prefetch_related("lines__product").get(account=user)

    return envelope_ok(data={
        "cart": CartSerializer(cart).data,
        "stale_lines": stale_lines,
    })


def validate_cart_for_checkout(user):
    cart, _ = Cart.objects.get_or_create(account=user)
    lines = cart.lines.select_related("product").all()

    if not lines.exists():
        return envelope_error("empty_cart", "Cart is empty.", status=status.HTTP_400_BAD_REQUEST)

    for line in lines:
        if not line.product.is_active:
            return envelope_error("cart_changed", f"Product {line.product.name} is no longer available.", status=status.HTTP_409_CONFLICT)

        if AvailabilityBlock.objects.filter(
            product=line.product,
            start_date__lte=line.rental_end,
            end_date__gte=line.rental_start,
        ).exists():
            return envelope_error("cart_changed", f"Product {line.product.name} is no longer available for selected dates.", status=status.HTTP_409_CONFLICT)

    return envelope_ok(data={"valid": True, "cart": CartSerializer(cart).data})

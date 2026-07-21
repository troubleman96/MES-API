from django.db.models import Q
from rest_framework import status

from apps.accounts.models import Account
from apps.core.responses import envelope_error, envelope_ok
from apps.equipment.models import AvailabilityBlock, Product
from apps.equipment.serializers import (
    AvailabilityBlockSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


def list_products(query_params):
    qs = Product.objects.filter(is_active=True).prefetch_related("images")

    category = query_params.get("category")
    if category:
        qs = qs.filter(category=category)

    search = query_params.get("search")
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

    return qs


def get_product(product_id):
    try:
        product = Product.objects.prefetch_related("images").select_related("merchant").get(id=product_id)
    except Product.DoesNotExist:
        return None
    return product


def check_availability(product_id):
    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return envelope_error("not_found", "Product not found.", status=status.HTTP_404_NOT_FOUND)

    blocks = AvailabilityBlock.objects.filter(
        product=product,
        reason="booked",
    ).order_by("start_date")

    return envelope_ok(data={
        "blocked_ranges": AvailabilityBlockSerializer(blocks, many=True).data,
    })


def list_merchants(query_params):
    from django.db.models import Count
    qs = Account.objects.filter(
        role="merchant",
        is_verified_merchant=True,
        is_active=True,
    ).annotate(_product_count=Count("products"))

    search = query_params.get("search")
    if search:
        qs = qs.filter(
            Q(business_name__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )

    return qs.order_by("-_product_count")


def get_merchant(merchant_id):
    from django.db.models import Count
    try:
        merchant = Account.objects.filter(role="merchant").annotate(
            _product_count=Count("products")
        ).get(id=merchant_id)
    except Account.DoesNotExist:
        return None
    return merchant


def create_listing(user, data):
    serializer = ProductDetailSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    product = serializer.save(merchant=user)
    return envelope_ok(data=ProductDetailSerializer(product).data, status=status.HTTP_201_CREATED)


def update_listing(user, product_id, data):
    try:
        product = Product.objects.get(id=product_id, merchant=user)
    except Product.DoesNotExist:
        return envelope_error("not_found", "Product not found.", status=status.HTTP_404_NOT_FOUND)

    serializer = ProductDetailSerializer(product, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    product = serializer.save()
    return envelope_ok(data=ProductDetailSerializer(product).data)


def delete_listing(user, product_id):
    try:
        product = Product.objects.get(id=product_id, merchant=user)
    except Product.DoesNotExist:
        return envelope_error("not_found", "Product not found.", status=status.HTTP_404_NOT_FOUND)

    product.is_active = False
    product.save(update_fields=["is_active"])
    return envelope_ok(status=status.HTTP_204_NO_CONTENT)


def list_merchant_products(user):
    products = Product.objects.filter(merchant=user).prefetch_related("images")
    return envelope_ok(data=ProductListSerializer(products, many=True).data)

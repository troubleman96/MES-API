from rest_framework import serializers

from apps.bookings.models import OrderGroup, SubOrder, SubOrderLine


class SubOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubOrderLine
        fields = [
            "id", "product", "product_name_snapshot", "daily_rate_snapshot_tzs",
            "rental_start", "rental_end", "quantity", "line_total_tzs",
        ]


class SubOrderSerializer(serializers.ModelSerializer):
    lines = SubOrderLineSerializer(many=True, read_only=True)
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)

    class Meta:
        model = SubOrder
        fields = [
            "id", "order_group", "merchant", "merchant_name", "status",
            "special_instructions", "subtotal_tzs", "lines", "created_at",
        ]


class SubOrderListSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)

    class Meta:
        model = SubOrder
        fields = ["id", "merchant_name", "subtotal_tzs", "status", "created_at"]


class OrderGroupSerializer(serializers.ModelSerializer):
    sub_orders = SubOrderListSerializer(many=True, read_only=True)

    class Meta:
        model = OrderGroup
        fields = ["id", "buyer", "delivery_address", "billing_address", "sub_orders", "created_at"]


class CheckoutSerializer(serializers.Serializer):
    delivery_address_id = serializers.UUIDField()
    billing_address_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, default="")


class SubOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SubOrder.STATUS_CHOICES)

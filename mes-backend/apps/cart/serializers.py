from rest_framework import serializers

from apps.cart.models import Cart, CartLine


class CartLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    daily_rate_tzs = serializers.IntegerField(source="product.daily_rate_tzs", read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    merchant_name = serializers.CharField(source="product.merchant.business_name", read_only=True)
    merchant_id = serializers.CharField(source="product.merchant.id", read_only=True)

    class Meta:
        model = CartLine
        fields = [
            "id", "product", "product_name", "daily_rate_tzs",
            "rental_start", "rental_end", "quantity", "added_at",
            "thumbnail_url", "merchant_name", "merchant_id",
        ]

    def get_thumbnail_url(self, obj):
        first_image = obj.product.images.first()
        return first_image.url if first_image else ""


class CartSerializer(serializers.ModelSerializer):
    lines = CartLineSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ["account", "lines", "updated_at"]
        read_only_fields = ["account", "updated_at"]


class CartSyncSerializer(serializers.Serializer):
    lines = CartLineSerializer(many=True)

from rest_framework import serializers

from apps.equipment.models import AvailabilityBlock, Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "url", "sort_order"]


class ProductListSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "category", "daily_rate_tzs",
            "is_featured", "is_active", "created_at", "images",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "merchant", "merchant_name", "name", "category",
            "description", "specs", "daily_rate_tzs", "is_featured",
            "is_active", "created_at", "images",
        ]


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "name", "category", "description", "specs",
            "daily_rate_tzs", "is_featured", "is_active",
        ]


class AvailabilityBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityBlock
        fields = ["start_date", "end_date"]
        read_only_fields = fields

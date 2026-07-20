from rest_framework import serializers

from apps.addresses.models import Address


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id", "label", "facility_name", "address_line1", "address_line2",
            "ward", "district", "city", "contact_name", "contact_phone",
            "delivery_notes", "address_type", "is_default", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

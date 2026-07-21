from django.contrib import admin

from .models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "label", "account", "facility_name", "city", "district",
        "address_type", "is_default",
    )
    list_filter = ("address_type", "is_default", "city")
    search_fields = (
        "facility_name", "address_line1", "city", "district",
        "contact_name", "account__email",
    )
    raw_id_fields = ("account",)

from django.contrib import admin

from .models import OrderGroup, SubOrder, SubOrderLine


class SubOrderInline(admin.TabularInline):
    model = SubOrder
    extra = 0
    raw_id_fields = ("merchant",)
    readonly_fields = ("subtotal_tzs", "created_at")
    fields = ("merchant", "status", "subtotal_tzs", "special_instructions", "created_at")


class SubOrderLineInline(admin.TabularInline):
    model = SubOrderLine
    extra = 0
    raw_id_fields = ("product",)
    readonly_fields = (
        "product_name_snapshot", "daily_rate_snapshot_tzs",
        "rental_start", "rental_end", "quantity", "line_total_tzs",
    )


@admin.register(OrderGroup)
class OrderGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "created_at")
    raw_id_fields = ("buyer", "delivery_address", "billing_address")
    search_fields = ("buyer__email",)
    inlines = [SubOrderInline]


@admin.register(SubOrder)
class SubOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "order_group", "merchant", "status",
        "subtotal_tzs", "created_at",
    )
    list_filter = ("status",)
    raw_id_fields = ("order_group", "merchant")
    search_fields = (
        "merchant__business_name", "order_group__buyer__email",
    )
    inlines = [SubOrderLineInline]


@admin.register(SubOrderLine)
class SubOrderLineAdmin(admin.ModelAdmin):
    list_display = (
        "sub_order", "product_name_snapshot", "daily_rate_snapshot_tzs",
        "rental_start", "rental_end", "quantity", "line_total_tzs",
    )
    raw_id_fields = ("sub_order", "product")

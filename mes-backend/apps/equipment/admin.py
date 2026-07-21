from django.contrib import admin

from .models import AvailabilityBlock, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("url", "sort_order")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "merchant", "category", "daily_rate_tzs",
        "is_featured", "is_active", "created_at",
    )
    list_filter = ("category", "is_featured", "is_active")
    search_fields = ("name", "description", "merchant__business_name")
    raw_id_fields = ("merchant",)
    inlines = [ProductImageInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "url", "sort_order")
    raw_id_fields = ("product",)


@admin.register(AvailabilityBlock)
class AvailabilityBlockAdmin(admin.ModelAdmin):
    list_display = ("product", "start_date", "end_date", "reason", "sub_order")
    list_filter = ("reason",)
    raw_id_fields = ("product", "sub_order")

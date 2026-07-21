from django.contrib import admin

from .models import Cart, CartLine


class CartLineInline(admin.TabularInline):
    model = CartLine
    extra = 0
    raw_id_fields = ("product",)
    readonly_fields = ("added_at",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("account", "updated_at")
    raw_id_fields = ("account",)
    inlines = [CartLineInline]
    search_fields = ("account__email",)


@admin.register(CartLine)
class CartLineAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "rental_start", "rental_end", "quantity")
    raw_id_fields = ("cart", "product")

from django.contrib import admin

from .models import PaymentIntent, WebhookEvent


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = (
        "sub_order", "snippe_reference", "status",
        "amount_tzs", "network", "expires_at", "created_at",
    )
    list_filter = ("status", "network")
    raw_id_fields = ("sub_order",)
    search_fields = ("snippe_reference",)
    readonly_fields = ("created_at",)


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("provider", "event_id", "received_at")
    list_filter = ("provider",)
    search_fields = ("event_id",)
    readonly_fields = ("received_at",)

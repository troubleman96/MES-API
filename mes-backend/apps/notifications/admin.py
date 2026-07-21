from django.contrib import admin

from .models import DeviceToken, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("account", "type", "title", "read_at", "created_at")
    list_filter = ("type", "read_at")
    search_fields = ("title", "body", "account__email")
    raw_id_fields = ("account",)
    readonly_fields = ("created_at",)


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("account", "fcm_token", "registered_at")
    raw_id_fields = ("account",)
    search_fields = ("fcm_token", "account__email")
    readonly_fields = ("registered_at",)

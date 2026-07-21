import string
import random

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.core.cache import cache

from .models import Account


@admin.register(Account)
class AccountAdmin(UserAdmin):
    model = Account
    list_display = (
        "email", "first_name", "last_name", "role", "phone",
        "phone_verified", "is_verified_merchant", "is_active", "created_at",
    )
    list_filter = ("role", "phone_verified", "is_verified_merchant", "is_active")
    search_fields = ("email", "first_name", "last_name", "business_name", "phone")
    ordering = ("-created_at",)
    actions = ["resend_phone_otp", "verify_phone_manually", "mark_merchant_verified"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {
            "fields": (
                "first_name", "last_name", "phone", "phone_verified",
                "role", "facility_name", "business_name",
            ),
        }),
        ("Permissions", {
            "fields": (
                "is_active", "is_staff", "is_superuser",
                "is_verified_merchant", "groups", "user_permissions",
            ),
        }),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", "first_name", "last_name", "role", "phone",
                "password1", "password2",
            ),
        }),
    )

    @admin.action(description="Resend phone OTP via SMS")
    def resend_phone_otp(self, request, queryset):
        from apps.notifications.clients import SendAfricaClient
        client = SendAfricaClient()
        sent = 0
        failed = []
        for user in queryset:
            if not user.phone:
                failed.append(f"{user.email} (no phone number)")
                continue
            otp = "".join(random.choices(string.digits, k=6))
            msg = f"Your MES verification code is: {otp}. Valid for 15 minutes."
            ok = client.send_sms(user.phone, msg)
            if ok:
                cache.set(f"otp:{user.id}:phone_verify", otp, timeout=900)
                sent += 1
            else:
                failed.append(f"{user.email} (SMS failed)")
        if sent:
            self.message_user(request, f"OTP sent to {sent} user(s).", messages.SUCCESS)
        if failed:
            self.message_user(request, f"Failed: {'; '.join(failed)}", messages.WARNING)

    @admin.action(description="Mark phone as verified (skip OTP)")
    def verify_phone_manually(self, request, queryset):
        count = queryset.filter(phone_verified=False).update(phone_verified=True)
        if count:
            self.message_user(request, f"Verified {count} user(s) phone.", messages.SUCCESS)
        else:
            self.message_user(request, "All selected users already verified.", messages.INFO)

    @admin.action(description="Mark as verified merchant")
    def mark_merchant_verified(self, request, queryset):
        count = queryset.filter(is_verified_merchant=False).update(is_verified_merchant=True)
        if count:
            self.message_user(request, f"Verified {count} merchant(s).", messages.SUCCESS)
        else:
            self.message_user(request, "All selected merchants already verified.", messages.INFO)

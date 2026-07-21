from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

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

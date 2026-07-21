from django.contrib import admin

from .models import Contract, Signature


class SignatureInline(admin.TabularInline):
    model = Signature
    extra = 0
    raw_id_fields = ("signer",)
    readonly_fields = ("signed_at",)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("sub_order", "pdf_url", "generated_at")
    raw_id_fields = ("sub_order",)
    inlines = [SignatureInline]


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ("contract", "signer", "signed_at")
    raw_id_fields = ("contract", "signer")

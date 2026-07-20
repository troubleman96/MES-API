import uuid

from django.db import models


class Address(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=50)
    facility_name = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=16)
    delivery_notes = models.TextField(blank=True)
    address_type = models.CharField(
        choices=[("delivery", "Delivery"), ("billing", "Billing"), ("both", "Both")],
        default="both",
        max_length=10,
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "addresses"
        ordering = ["-is_default", "-created_at"]

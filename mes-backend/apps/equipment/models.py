import uuid

from django.db import models


class Product(models.Model):
    CATEGORY_CHOICES = [
        ("diagnostic", "Diagnostic"),
        ("rehabilitation", "Rehabilitation"),
        ("life_support", "Life Support"),
        ("mobility", "Mobility"),
        ("sterilization", "Sterilization"),
        ("monitoring", "Monitoring"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=20)
    description = models.TextField()
    specs = models.JSONField(default=dict)
    daily_rate_tzs = models.PositiveIntegerField()
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    url = models.URLField()
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "product_images"
        ordering = ["sort_order"]


class AvailabilityBlock(models.Model):
    REASON_CHOICES = [
        ("booked", "Booked"),
        ("maintenance", "Maintenance"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="blocked_ranges")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(choices=REASON_CHOICES, max_length=15)
    sub_order = models.ForeignKey("bookings.SubOrder", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "availability_blocks"
        ordering = ["start_date"]

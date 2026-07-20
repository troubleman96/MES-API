import uuid

from django.db import models


class OrderGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="order_groups")
    delivery_address = models.ForeignKey("addresses.Address", on_delete=models.PROTECT, related_name="+")
    billing_address = models.ForeignKey("addresses.Address", on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_groups"
        ordering = ["-created_at"]


class SubOrder(models.Model):
    STATUS_CHOICES = [
        ("pending_payment", "Pending Payment"),
        ("confirmed", "Confirmed"),
        ("dispatched", "Dispatched"),
        ("delivered", "Delivered"),
        ("return_due", "Return Due"),
        ("returned", "Returned"),
        ("cancelled", "Cancelled"),
        ("payment_failed", "Payment Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_group = models.ForeignKey(OrderGroup, on_delete=models.CASCADE, related_name="sub_orders")
    merchant = models.ForeignKey("accounts.Account", on_delete=models.PROTECT, related_name="incoming_orders")
    status = models.CharField(choices=STATUS_CHOICES, default="pending_payment", max_length=20)
    special_instructions = models.TextField(blank=True)
    subtotal_tzs = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sub_orders"
        ordering = ["-created_at"]


class SubOrderLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.ForeignKey(SubOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("equipment.Product", on_delete=models.PROTECT)
    product_name_snapshot = models.CharField(max_length=255)
    daily_rate_snapshot_tzs = models.PositiveIntegerField()
    rental_start = models.DateField()
    rental_end = models.DateField()
    quantity = models.PositiveSmallIntegerField()
    line_total_tzs = models.PositiveIntegerField()

    class Meta:
        db_table = "sub_order_lines"

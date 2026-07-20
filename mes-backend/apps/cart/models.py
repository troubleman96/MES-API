import uuid

from django.db import models


class Cart(models.Model):
    account = models.OneToOneField("accounts.Account", on_delete=models.CASCADE, primary_key=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carts"


class CartLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("equipment.Product", on_delete=models.CASCADE)
    rental_start = models.DateField()
    rental_end = models.DateField()
    quantity = models.PositiveSmallIntegerField(default=1)
    added_at = models.DateTimeField()

    class Meta:
        db_table = "cart_lines"

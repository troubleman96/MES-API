import uuid

from django.db import models


class Contract(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.OneToOneField("bookings.SubOrder", on_delete=models.CASCADE, related_name="contract")
    pdf_url = models.URLField()
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contracts"


class Signature(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="signatures")
    signer = models.ForeignKey("accounts.Account", on_delete=models.PROTECT)
    signature_image_url = models.URLField()
    signed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "signatures"

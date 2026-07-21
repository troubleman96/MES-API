import hashlib
import hmac
import uuid

import requests
from django.conf import settings


class SnippeClient:
    BASE_URL = "https://api.snippe.sh"

    def __init__(self):
        self.api_key = settings.SNIPPE_API_KEY

    def initiate_payment(
        self,
        amount_tzs: int,
        phone: str,
        first_name: str,
        last_name: str,
        email: str = "",
        description: str = "",
    ) -> dict:
        payload = {
            "payment_type": "mobile",
            "details": {
                "amount": amount_tzs,
                "currency": "TZS",
            },
            "phone_number": phone,
            "customer": {
                "firstname": first_name,
                "lastname": last_name,
                "email": email,
            },
            "webhook_url": settings.SNIPPE_WEBHOOK_URL,
            "metadata": {
                "description": description,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": str(uuid.uuid4()),
        }
        response = requests.post(
            f"{self.BASE_URL}/v1/payments",
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        return body.get("data", body)

    def verify_webhook_signature(
        self, payload_body: bytes, timestamp: str, signature_header: str
    ) -> bool:
        secret = settings.SNIPPE_WEBHOOK_SECRET.encode("utf-8")
        message = f"{timestamp}.{payload_body.decode('utf-8')}"
        expected = hmac.new(secret, message.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)

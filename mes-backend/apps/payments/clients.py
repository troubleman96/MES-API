import hashlib
import hmac
import json
import time
import uuid
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone


class SnippeClient:
    BASE_URL = "https://api.snippe.com/v1"

    def __init__(self):
        self.api_key = settings.SNIPPE_API_KEY

    def initiate_payment(self, amount_tzs: int, phone: str, description: str) -> dict:
        payload = {
            "amount": amount_tzs,
            "currency": "TZS",
            "phone": phone,
            "description": description,
            "reference": str(uuid.uuid4()),
            "callback_url": settings.SNIPPE_WEBHOOK_URL,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(f"{self.BASE_URL}/payments", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def verify_webhook_signature(self, payload_body: bytes, signature_header: str) -> bool:
        secret = settings.SNIPPE_WEBHOOK_SECRET.encode("utf-8")
        expected = hmac.new(secret, payload_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)

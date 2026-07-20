import requests
from django.conf import settings


class SendAfricaClient:
    BASE_URL = "https://api.sendafrica.com/v1"

    def __init__(self):
        self.api_key = settings.SENDAFRICA_API_KEY

    def send_sms(self, phone_number: str, message: str) -> bool:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": phone_number,
            "message": message,
        }
        try:
            response = requests.post(
                f"{self.BASE_URL}/sms/send",
                json=payload,
                headers=headers,
                timeout=30,
            )
            return response.status_code in (200, 201, 202)
        except requests.RequestException:
            return False

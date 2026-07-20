from django.urls import path

from apps.payments.webhooks import snippe_webhook

urlpatterns = [
    path("snippe/", snippe_webhook, name="snippe_webhook"),
]

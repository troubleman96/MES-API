from django.urls import path

from apps.payments import views

urlpatterns = [
    path("<uuid:pk>/pay/", views.PayView.as_view(), name="pay"),
    path("<uuid:pk>/payment-status/", views.PaymentStatusView.as_view(), name="payment_status"),
]

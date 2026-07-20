from django.urls import path

from apps.cart import views

urlpatterns = [
    path("", views.CartView.as_view(), name="cart"),
]

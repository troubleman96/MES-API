from django.urls import path

from apps.bookings import views

urlpatterns = [
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("orders/", views.OrderListView.as_view(), name="order_list"),
    path("orders/<uuid:pk>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("orders/<uuid:pk>/status/", views.OrderStatusUpdateView.as_view(), name="order_status"),
]

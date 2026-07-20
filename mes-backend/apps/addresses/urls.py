from django.urls import path

from apps.addresses import views

urlpatterns = [
    path("", views.AddressListView.as_view(), name="address_list"),
    path("<uuid:pk>/", views.AddressDetailView.as_view(), name="address_detail"),
]

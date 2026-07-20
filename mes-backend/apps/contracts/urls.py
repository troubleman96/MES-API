from django.urls import path

from apps.contracts import views

urlpatterns = [
    path("orders/<uuid:pk>/contract/", views.ContractView.as_view(), name="contract"),
    path("orders/<uuid:pk>/contract/sign/", views.ContractSignView.as_view(), name="contract_sign"),
]

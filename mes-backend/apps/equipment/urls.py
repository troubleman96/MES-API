from django.urls import path

from apps.equipment import views

urlpatterns = [
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/<uuid:pk>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("products/<uuid:pk>/availability/", views.ProductAvailabilityView.as_view(), name="product_availability"),
    path("products/", views.ProductCreateView.as_view(), name="product_create"),
    path("products/<uuid:pk>/", views.ProductUpdateView.as_view(), name="product_update"),
    path("products/<uuid:pk>/", views.ProductDeleteView.as_view(), name="product_delete"),
    path("merchants/<uuid:pk>/", views.MerchantDetailView.as_view(), name="merchant_detail"),
    path("merchants/me/products/", views.MerchantProductListView.as_view(), name="merchant_product_list"),
]

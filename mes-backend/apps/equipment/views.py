from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import MesPagination
from apps.core.permissions import IsMerchant, IsOwnerMerchant
from apps.core.responses import envelope_error, envelope_ok
from apps.equipment import services
from apps.equipment.models import Product
from apps.equipment.serializers import (
    MerchantDetailSerializer,
    MerchantListSerializer,
    ProductCreateUpdateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


class ProductListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        products = services.list_products(request.query_params)
        paginator = MesPagination()
        page = paginator.paginate_queryset(products, request)
        serializer = ProductListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        return services.create_listing(request.user, request.data)


class ProductDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        if self.request.method in ("PUT", "DELETE"):
            return [permissions.IsAuthenticated(), IsMerchant()]
        return [permissions.AllowAny()]

    def get(self, request, pk):
        product = services.get_product(pk)
        if product is None:
            return envelope_error("not_found", "Product not found.", status=404)
        return envelope_ok(data=ProductDetailSerializer(product).data)

    def put(self, request, pk):
        return services.update_listing(request.user, pk, request.data)

    def delete(self, request, pk):
        return services.delete_listing(request.user, pk)


class ProductAvailabilityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        return services.check_availability(pk)


class MerchantListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        merchants = services.list_merchants(request.query_params)
        paginator = MesPagination()
        page = paginator.paginate_queryset(merchants, request)
        serializer = MerchantListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class MerchantDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        merchant = services.get_merchant(pk)
        if merchant is None:
            return envelope_error("not_found", "Merchant not found.", status=404)
        return envelope_ok(data=MerchantDetailSerializer(merchant).data)


class MerchantProductListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsMerchant]

    def get(self, request):
        return services.list_merchant_products(request.user)


class ProductCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsMerchant]

    def post(self, request):
        return services.create_listing(request.user, request.data)


class ProductUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsMerchant, IsOwnerMerchant]

    def put(self, request, pk):
        return services.update_listing(request.user, pk, request.data)


class ProductDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsMerchant, IsOwnerMerchant]

    def delete(self, request, pk):
        return services.delete_listing(request.user, pk)

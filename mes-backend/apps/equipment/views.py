from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import MesPagination
from apps.core.permissions import IsMerchant, IsOwnerMerchant
from apps.equipment import services
from apps.equipment.models import Product
from apps.equipment.serializers import (
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


class ProductDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        product = services.get_product(pk)
        if product is None:
            return Response({"detail": "Not found."}, status=404)
        return Response(ProductDetailSerializer(product).data)


class ProductAvailabilityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        return services.check_availability(pk)


class MerchantDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        merchant = services.get_merchant(pk)
        if merchant is None:
            return Response({"detail": "Not found."}, status=404)
        return Response({
            "id": str(merchant.id),
            "business_name": merchant.business_name,
            "is_verified_merchant": merchant.is_verified_merchant,
        })


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

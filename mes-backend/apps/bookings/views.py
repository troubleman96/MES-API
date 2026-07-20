from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings import services
from apps.bookings.serializers import CheckoutSerializer, SubOrderStatusSerializer
from apps.core.permissions import IsBuyer, IsMerchant


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBuyer]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.checkout(request.user, serializer.validated_data)


class OrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return services.list_orders(request.user, request.query_params)


class OrderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        return services.get_order(request.user, pk)


class OrderStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsMerchant]

    def patch(self, request, pk):
        serializer = SubOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.update_order_status(request.user, pk, serializer.validated_data["status"])

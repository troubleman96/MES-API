from rest_framework import permissions
from rest_framework.views import APIView

from apps.cart import services
from apps.cart.serializers import CartSyncSerializer
from apps.core.permissions import IsBuyer


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBuyer]

    def get(self, request):
        return services.get_cart(request.user)

    def patch(self, request):
        serializer = CartSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.replace_cart(request.user, serializer.validated_data["lines"])

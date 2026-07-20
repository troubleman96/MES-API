from rest_framework import permissions
from rest_framework.views import APIView

from apps.payments import services


class PayView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        return services.create_payment(request.user, pk)


class PaymentStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        return services.get_payment_status(request.user, pk)

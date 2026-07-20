from rest_framework import permissions
from rest_framework.views import APIView

from apps.contracts import services
from apps.contracts.serializers import SignContractSerializer


class ContractView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        return services.get_contract(request.user, pk)


class ContractSignView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        serializer = SignContractSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.sign_contract(request.user, pk, serializer.validated_data)

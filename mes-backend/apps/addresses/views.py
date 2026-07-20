from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.addresses import services
from apps.core.permissions import IsBuyer


class AddressListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBuyer]

    def get(self, request):
        return services.list_addresses(request.user)

    def post(self, request):
        return services.create_address(request.user, request.data)


class AddressDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBuyer]

    def put(self, request, pk):
        return services.update_address(request.user, pk, request.data)

    def delete(self, request, pk):
        return services.delete_address(request.user, pk)

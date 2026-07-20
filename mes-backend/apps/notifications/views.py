from rest_framework import permissions
from rest_framework.views import APIView

from apps.notifications import services
from apps.notifications.serializers import DeviceTokenSerializer


class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return services.list_notifications(request.user)


class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return services.unread_count(request.user)


class NotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        return services.mark_read(request.user, pk)


class NotificationReadAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return services.mark_all_read(request.user)


class DeviceTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.register_device(request.user, serializer.validated_data["fcm_token"])

from django.urls import path

from apps.notifications import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification_list"),
    path("unread-count/", views.NotificationUnreadCountView.as_view(), name="notification_unread_count"),
    path("<uuid:pk>/read/", views.NotificationReadView.as_view(), name="notification_read"),
    path("read-all/", views.NotificationReadAllView.as_view(), name="notification_read_all"),
    path("register-device/", views.DeviceTokenView.as_view(), name="register_device"),
]

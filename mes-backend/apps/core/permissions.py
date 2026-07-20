from rest_framework.permissions import BasePermission


class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == "buyer")


class IsMerchant(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == "merchant")


class IsOwnerMerchant(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.merchant_id == request.user.id

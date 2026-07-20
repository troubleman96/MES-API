from django.db import transaction
from rest_framework import status

from apps.addresses.models import Address
from apps.addresses.serializers import AddressSerializer
from apps.core.responses import envelope_error, envelope_ok


def list_addresses(user):
    addresses = Address.objects.filter(account=user)
    return envelope_ok(data=AddressSerializer(addresses, many=True).data)


def create_address(user, data):
    data["account"] = user.id
    serializer = AddressSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    address = serializer.save(account=user)

    if address.is_default:
        _unset_other_defaults(user, address.id)

    return envelope_ok(data=AddressSerializer(address).data, status=status.HTTP_201_CREATED)


def update_address(user, address_id, data):
    try:
        address = Address.objects.get(id=address_id, account=user)
    except Address.DoesNotExist:
        return envelope_error("not_found", "Address not found.", status=status.HTTP_404_NOT_FOUND)

    serializer = AddressSerializer(address, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    address = serializer.save()

    if address.is_default:
        _unset_other_defaults(user, address.id)

    return envelope_ok(data=AddressSerializer(address).data)


def delete_address(user, address_id):
    try:
        address = Address.objects.get(id=address_id, account=user)
    except Address.DoesNotExist:
        return envelope_error("not_found", "Address not found.", status=status.HTTP_404_NOT_FOUND)

    address.delete()
    return envelope_ok(status=status.HTTP_204_NO_CONTENT)


def set_default(user, address_id):
    try:
        address = Address.objects.get(id=address_id, account=user)
    except Address.DoesNotExist:
        return envelope_error("not_found", "Address not found.", status=status.HTTP_404_NOT_FOUND)

    with transaction.atomic():
        Address.objects.filter(account=user, is_default=True).exclude(id=address_id).update(is_default=False)
        address.is_default = True
        address.save(update_fields=["is_default"])

    return envelope_ok(data=AddressSerializer(address).data)


def _unset_other_defaults(user, exclude_id):
    Address.objects.filter(account=user, is_default=True).exclude(id=exclude_id).update(is_default=False)

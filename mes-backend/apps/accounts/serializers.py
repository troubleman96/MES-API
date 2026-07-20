import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import Account


class RegisterSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Account._meta.get_field("role").choices)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=12)
    phone = serializers.RegexField(regex=r"^\+?[0-9]{10,15}$", required=False)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    facility_name = serializers.CharField(max_length=255, required=False)
    business_name = serializers.CharField(max_length=255, required=False)

    def validate_email(self, value):
        if Account.objects.filter(email=value).exists():
            raise serializers.ValidationError("Account with this email already exists.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        role = attrs.get("role")
        if role == "buyer" and not attrs.get("facility_name"):
            raise serializers.ValidationError({"facility_name": "Required for buyer accounts."})
        if role == "merchant" and not attrs.get("business_name"):
            raise serializers.ValidationError({"business_name": "Required for merchant accounts."})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id", "email", "phone", "phone_verified", "role",
            "first_name", "last_name", "facility_name", "business_name",
            "is_verified_merchant", "created_at", "profile_complete",
        ]
        read_only_fields = ["id", "email", "role", "is_verified_merchant", "created_at", "profile_complete"]


class AccountUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "first_name", "last_name", "phone",
            "facility_name", "business_name",
        ]


class SendPhoneOTPSerializer(serializers.Serializer):
    phone = serializers.RegexField(regex=r"^\+?[0-9]{10,15}$")


class VerifyPhoneSerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=6)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ForgotPasswordConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(min_length=12)

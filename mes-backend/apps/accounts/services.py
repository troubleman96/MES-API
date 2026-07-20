import random
import string

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.responses import envelope_error, envelope_ok

Account = get_user_model()


def register(data):
    if Account.objects.filter(email=data["email"]).exists():
        return envelope_error("email_exists", "An account with this email already exists.", status=status.HTTP_409_CONFLICT)

    account = Account.objects.create_user(
        email=data["email"],
        password=data["password"],
        role=data["role"],
        phone=data.get("phone"),
        first_name=data["first_name"],
        last_name=data["last_name"],
        facility_name=data.get("facility_name", ""),
        business_name=data.get("business_name", ""),
    )
    refresh = RefreshToken.for_user(account)
    return envelope_ok(
        data={
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "role": account.role,
            "profile_complete": account.profile_complete,
        },
        status=status.HTTP_201_CREATED,
    )


def login(email, password):
    try:
        account = Account.objects.get(email=email)
    except Account.DoesNotExist:
        return envelope_error("invalid_credentials", "Invalid email or password.", status=status.HTTP_401_UNAUTHORIZED)

    if not account.check_password(password):
        return envelope_error("invalid_credentials", "Invalid email or password.", status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(account)
    return envelope_ok(data={
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
        "expires_in": int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        "role": account.role,
        "phone_verified": account.phone_verified,
        "profile_complete": account.profile_complete,
    })


def refresh_token(refresh_token_str):
    try:
        refresh = RefreshToken(refresh_token_str)
        return envelope_ok(data={
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        })
    except Exception:
        return envelope_error("invalid_refresh_token", "Invalid or expired refresh token.", status=status.HTTP_401_UNAUTHORIZED)


def get_profile(user):
    from apps.accounts.serializers import AccountSerializer
    return envelope_ok(data=AccountSerializer(user).data)


def update_profile(user, data):
    from apps.accounts.serializers import AccountUpdateSerializer
    serializer = AccountUpdateSerializer(user, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return envelope_ok(data=AccountSerializer(user).data)


def send_phone_otp(user, phone):
    otp = "".join(random.choices(string.digits, k=6))
    from apps.notifications.clients import SendAfricaClient
    client = SendAfricaClient()
    result = client.send_sms(phone, f"Your MES verification code is: {otp}. Valid for 15 minutes.")
    if not result:
        return envelope_error("sms_failed", "Failed to send verification code.", status=status.HTTP_502_BAD_GATEWAY)

    user.phone = phone
    user._otp = otp
    user._otp_type = "phone_verify"
    user.save(update_fields=["phone"])

    from django.core.cache import cache
    cache.set(f"otp:{user.id}:phone_verify", otp, timeout=900)

    return envelope_ok(data={"message": "OTP sent successfully."})


def verify_phone(user, otp):
    from django.core.cache import cache
    stored_otp = cache.get(f"otp:{user.id}:phone_verify")
    if not stored_otp or stored_otp != otp:
        return envelope_error("invalid_otp", "Invalid or expired OTP.", status=status.HTTP_400_BAD_REQUEST)

    user.phone_verified = True
    user.save(update_fields=["phone_verified"])
    cache.delete(f"otp:{user.id}:phone_verify")
    return envelope_ok(data={"message": "Phone verified successfully."})


def forgot_password(email):
    try:
        account = Account.objects.get(email=email)
    except Account.DoesNotExist:
        return envelope_ok(data={"message": "If an account exists, a reset code has been sent."})

    otp = "".join(random.choices(string.digits, k=6))
    from django.core.cache import cache
    cache.set(f"otp:{account.id}:forgot_password", otp, timeout=900)

    if account.phone:
        from apps.notifications.clients import SendAfricaClient
        client = SendAfricaClient()
        client.send_sms(account.phone, f"Your MES password reset code is: {otp}. Valid for 15 minutes.")

    return envelope_ok(data={"message": "If an account exists, a reset code has been sent."})


def forgot_password_confirm(email, otp, new_password):
    try:
        account = Account.objects.get(email=email)
    except Account.DoesNotExist:
        return envelope_error("invalid_credentials", "Invalid request.", status=status.HTTP_400_BAD_REQUEST)

    from django.core.cache import cache
    stored_otp = cache.get(f"otp:{account.id}:forgot_password")
    if not stored_otp or stored_otp != otp:
        return envelope_error("invalid_otp", "Invalid or expired OTP.", status=status.HTTP_400_BAD_REQUEST)

    account.set_password(new_password)
    account.save(update_fields=["password"])
    cache.delete(f"otp:{account.id}:forgot_password")
    return envelope_ok(data={"message": "Password reset successfully."})

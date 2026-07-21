from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.serializers import (
    AccountSerializer,
    ForgotPasswordConfirmSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    SendPhoneOTPSerializer,
    VerifyPhoneSerializer,
)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.register(serializer.validated_data)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.login(
            serializer.validated_data["email"],
            serializer.validated_data["password"],
        )


from apps.core.responses import envelope_error

class RefreshTokenView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return envelope_error("missing_token", "refresh_token is required.", status=status.HTTP_400_BAD_REQUEST)
        return services.refresh_token(refresh_token)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return services.refresh_token(None)


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return services.get_profile(request.user)

    def patch(self, request):
        return services.update_profile(request.user, request.data)


class SendPhoneOTPView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SendPhoneOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.send_phone_otp(request.user, serializer.validated_data["phone"])


class VerifyPhoneView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VerifyPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.verify_phone(request.user, serializer.validated_data["otp"])


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.forgot_password(serializer.validated_data["email"])


class ForgotPasswordConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.forgot_password_confirm(
            serializer.validated_data["email"],
            serializer.validated_data["otp"],
            serializer.validated_data["new_password"],
        )

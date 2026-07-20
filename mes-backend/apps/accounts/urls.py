from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", views.RefreshTokenView.as_view(), name="token_refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.ProfileView.as_view(), name="profile"),
    path("send-phone-otp/", views.SendPhoneOTPView.as_view(), name="send_phone_otp"),
    path("verify-phone/", views.VerifyPhoneView.as_view(), name="verify_phone"),
    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot_password"),
    path("forgot-password/confirm/", views.ForgotPasswordConfirmView.as_view(), name="forgot_password_confirm"),
]

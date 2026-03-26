from django.urls import path
from .views import RegisterView, VerifyRegisterOTPView, LoginView, VerifyLoginOTPView
from .views import LogoutView, ResendOTPView, ForgotPasswordView, ResetPasswordView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/',RegisterView.as_view(),name='register'),
    path('verify-register-otp/',VerifyRegisterOTPView.as_view(),name='verify_register_otp'),
    path('login/',LoginView.as_view(),name='login'),
    path('verify-login-otp/',VerifyLoginOTPView.as_view(),name='verify_login_otp'),
    path('logout/',LogoutView.as_view(),name='logout'),
    path('token/refresh/',TokenRefreshView.as_view(),name='token_refresh'),
]

from django.urls import path
from .views import RegisterView, VerifyRegisterOTPView, LoginView, VerifyLoginOTPView

urlpatterns = [
    path('register/',RegisterView.as_view(),name='register'),
    path('verify-register-otp/',VerifyRegisterOTPView.as_view(),name='verify_register_otp'),
    path('login/',LoginView.as_view(),name='login'),
    path('verify-login-otp/',VerifyLoginOTPView.as_view(),name='verify_login_otp'),
]

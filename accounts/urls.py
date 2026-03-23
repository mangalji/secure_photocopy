from django.urls import path
from .views import RegisterView, VerifyRegisterOTPView

urlpatterns = [
    path('register/',RegisterView.as_view(),name='register'),
    path('verify-otp/',VerifyRegisterOTPView.as_view(),name='verify_otp'),
]

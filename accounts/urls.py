from django.urls import path
from .views import RegisterView, VerifyRegisterOTPView, LoginView, VerifyLoginOTPView
from .views import LogoutView, ResendOTPView, ForgotPasswordView, ResetPasswordView
from .views import ShopRegisterView, ShopDeleteView, ShopDetailView, ShopListView, ShopUpdateView
from .views import DocumentUploadView, DocumentListView, DocumentDeleteView, PrintRequestCreateView
from .views import PrintRequestListView, PrintRequestCancleView, PrintConfirmView, PrintFailView, AccessDocumentView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('auth/register/',RegisterView.as_view(),name='register'),
    path('auth/verify-register-otp/',VerifyRegisterOTPView.as_view(),name='verify_register_otp'),
    path('auth/login/',LoginView.as_view(),name='login'),
    path('auth/verify-login-otp/',VerifyLoginOTPView.as_view(),name='verify_login_otp'),
    path('auth/logout/',LogoutView.as_view(),name='logout'),
    path('auth/token/refresh/',TokenRefreshView.as_view(),name='token_refresh'),
    path('auth/resend-otp/',ResendOTPView.as_view(),name='resend_otp'),
    path('auth/forgot-password/',ForgotPasswordView.as_view(),name='forgot_password'),
    path('auth/reset-password/',ResetPasswordView.as_view(),name='reset_password'),
    
    path('shops/register/',ShopRegisterView.as_view(),name='shop_register'),
    path('shops/list/',ShopListView.as_view(),name='shop_list'),
    path('shops/<int:shop_id>/',ShopDetailView.as_view(),name='shop_detail'),
    path('shops/<int:shop_id>/update/',ShopUpdateView.as_view(),name='shop_update'),
    path('shops/<int:shop_id>/delete/',ShopDeleteView.as_view(),name='shop_delete'),

    path('documents/upload/',DocumentUploadView.as_view(),name='document_upload'),
    path('documents/list/',DocumentListView.as_view(),name='document_list'),
    path('documents/<int:document_id>/delete/',DocumentDeleteView.as_view(),name='document_delete'),

    path('print-requests/lists/',PrintRequestListView.as_view(),name='print_request_list'),
    path('print-requests/create/',PrintRequestCreateView.as_view(),name='print_request_create'),
    path('print-requests/<int:request_id>/cancel/',PrintRequestCancleView.as_view(),name='print_request_cancle'),

    path('print-sessions/access/',AccessDocumentView.as_view(),name='access_document'),
    path('print-sessions/<int:session_id>/confirm/',PrintConfirmView.as_view(),name='print_confirm'),
    path('print-sessions/<int:session_id>/fail/',PrintFailView.as_view(),name='print_fail'),

    ]


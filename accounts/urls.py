from django.urls import path
from accounts.views.auth_views import RegisterView, LoginView, LogoutView
from accounts.views.shop_views import ShopRegisterView, ShopListView, ShopDetailView, ShopUpdateView, ShopDeleteView
from accounts.views.document_views import DocumentUploadView, DocumentListView, DocumentDeleteView
from accounts.views.resetpassword_views import ForgotPasswordView, ResetPasswordView, ChangePasswordView
from accounts.views.notification_views import NotificationListView, NotificationMarkReadView, NotificationMarkAllReadView
from accounts.views.otp_views import VerifyRegisterOTPView, VerifyLoginOTPView, ResendOTPView
from accounts.views.print_views import PrintRequestCreateView, PrintRequestListView, PrintRequestCancleView, PrintConfirmView, AccessDocumentView, PrintFailView
from accounts.views.profile_views import ProfileView, ProfileUpdateView
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

    path('notifications/list/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/mark-read/', NotificationMarkReadView.as_view(), name='notification_mark_read'),
    path('notifications/mark-read-all/',NotificationMarkAllReadView.as_view(),name='notification-marked-all-read'),

    path('profile/',ProfileView.as_view(),name='profile'),
    path('profile/update/',ProfileUpdateView.as_view(),name='profile-update'),
    path('profile/change-password/',ChangePasswordView.as_view(),name='change-password'),

    ]


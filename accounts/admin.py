from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models.auditlog_models import AuditLogs
from django.contrib.auth import get_user_model
from accounts.models.document_models import Document
from accounts.models.notification_models import Notification
from accounts.models.otp_models import OTP, OAuthConnection, MFABackupCode
from accounts.models.print_models import PrintRequest, PrintSession
from accounts.models.shop_models import Shops

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ['email', 'full_name', 'role', 'is_active', 'is_email_verified', 'created_at']
    list_filter   = ['role', 'is_active', 'is_email_verified', 'mfa_enabled']
    search_fields = ['email', 'full_name', 'phone']
    ordering      = ['-created_at']

    fieldsets = (
        ('Identity',    {'fields': ('email', 'full_name', 'phone', 'address', 'role')}),
        ('Password',    {'fields': ('password',)}),
        ('Status',      {'fields': ('is_active', 'is_email_verified', 'is_staff', 'is_superuser')}),
        ('MFA',         {'fields': ('mfa_enabled', 'mfa_secret')}),
        ('Timestamps',  {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields  = ['created_at', 'updated_at']
    add_fieldsets    = (
        (None, {
            'classes': ('wide',),
            'fields' : ('email', 'full_name', 'phone', 'role', 'password1', 'password2'),
        }),
    )

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display  = ['user', 'purpose', 'is_used', 'created_at', 'expires_at']
    list_filter   = ['purpose', 'is_used']
    search_fields = ['user__email']
    ordering      = ['-created_at']
    readonly_fields = ['otp_hash', 'created_at', 'used_at']

@admin.register(Shops)
class ShopAdmin(admin.ModelAdmin):
    list_display  = ['shop_name', 'shopkeeper', 'city', 'is_active', 'created_at']
    list_filter   = ['is_active', 'city']
    search_fields = ['shop_name', 'shopkeeper__email', 'shop_email']
    ordering      = ['-created_at']
    readonly_fields = ['created_at']

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display  = ['document_name', 'consumer', 'doc_type', 'file_size_mb', 'is_deleted', 'uploaded_at']
    list_filter   = ['is_deleted', 'doc_type']
    search_fields = ['document_name', 'consumer__email']
    ordering      = ['-uploaded_at']
    readonly_fields = ['uploaded_at', 'deleted_at', 'file_hash', 'encrypted_storage_ref', 'encryption_key_ref']

@admin.register(PrintRequest)
class PrintRequestAdmin(admin.ModelAdmin):
    list_display  = ['id', 'consumer', 'shop', 'status', 'is_token_used', 'requested_at']
    list_filter   = ['status', 'print_color', 'is_token_used']
    search_fields = ['consumer__email', 'shop__shop_name']
    ordering      = ['-requested_at']
    readonly_fields = ['access_token', 'requested_at', 'token_expires_at', 'expires_at']

@admin.register(PrintSession)
class PrintSessionAdmin(admin.ModelAdmin):
    list_display  = ['request', 'shopkeeper', 'session_status', 'document_accessed_at', 'print_completed_at']
    list_filter   = ['session_status']
    search_fields = ['shopkeeper__email', 'request__id']
    ordering      = ['-document_accessed_at']
    readonly_fields = ['document_accessed_at', 'ip_address', 'user_agent']

@admin.register(AuditLogs)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ['action', 'user', 'ip_address', 'created_at']
    list_filter   = ['action']
    search_fields = ['user__email', 'action', 'ip_address']
    ordering      = ['-created_at']
    readonly_fields = ['user', 'request', 'action', 'action_detail', 'ip_address', 'user_agent', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'notification_type', 'is_read', 'created_at']
    list_filter   = ['notification_type', 'is_read']
    search_fields = ['user__email']
    ordering      = ['-created_at']
    readonly_fields = ['created_at']

@admin.register(OAuthConnection)
class OAuthConnectionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'provider', 'provider_user_id', 'connected_at']
    list_filter   = ['provider']
    search_fields = ['user__email', 'provider_user_id']
    readonly_fields = ['connected_at', 'updated_at', 'access_token', 'refresh_token']

@admin.register(MFABackupCode)
class MFABackupCodeAdmin(admin.ModelAdmin):
    list_display  = ['user', 'is_used', 'created_at', 'used_at']
    list_filter   = ['is_used']
    search_fields = ['user__email']
    readonly_fields = ['code_hash', 'created_at', 'used_at']

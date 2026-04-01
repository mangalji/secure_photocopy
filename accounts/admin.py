from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models.auth_models import CustomUser
from accounts.models.auditlog_models import AuditLogs
from accounts.models.document_models import Document
from accounts.models.notification_models import Notification
from accounts.models.otp_models import OTP, MFABackupCode, OAuthConnection
from accounts.models.print_models import PrintRequest, PrintSession
from accounts.models.shop_models import Shops

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('user_id','full_name','email','phone','role','is_active','is_staff','is_email_verified')
    list_filter = ('role','is_active','is_staff','is_email_verified')
    search_fields = ('email','full_name','phone')
    ordering = ('user_id',)
    fieldsets = (
        (None, {'fields': ('email','password')}),
        ('Personal info', {'fields': ('full_name','phone','address','role')}),
        ('Permissions', {'fields': ('is_active','is_staff','is_superuser','is_email_verified','groups','user_permissions')}),
        ('Important dates', {'fields': ('last_login','created_at','updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email','full_name','phone','role','password1','password2','is_active','is_staff'),
        }),
    )


@admin.register(Shops)
class ShopsAdmin(admin.ModelAdmin):
    list_display = ('id','shopkeeper','shop_name','city','is_active','created_at')
    list_filter = ('city','is_active')
    search_fields = ('shop_name','shop_email','shop_phone','shopkeeper__email','shopkeeper__full_name')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('shopkeeper','shop_name','shop_email','shop_phone','shop_address','city','shop_license_no')}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('created_at','updated_at')}),
    )
    readonly_fields = ('created_at','updated_at',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('shopkeeper','shop_name','shop_email','shop_phone','shop_address','city','shop_license_no','is_active'),
        }),
    )


admin.site.register(OTP)
admin.site.register(MFABackupCode)
admin.site.register(OAuthConnection)
admin.site.register(AuditLogs)
admin.site.register(Document)
admin.site.register(PrintRequest)
admin.site.register(PrintSession)
admin.site.register(Notification)




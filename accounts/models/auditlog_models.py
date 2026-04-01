from django.db import models
from .auth_models import CustomUser
from .print_models import PrintRequest

class AuditLogs(models.Model):

    class Meta:
        db_table = 'audit_logs'

    class Action(models.TextChoices):
        USER_REGISTERED       = 'user_registered',       'User Registered'
        OTP_SENT              = 'otp_sent',              'OTP Sent'
        OTP_VERIFIED          = 'otp_verified',          'OTP Verified'
        OTP_FAILED            = 'otp_failed',            'OTP Failed'
        USER_LOGIN            = 'user_login',            'User Login'
        USER_LOGOUT           = 'user_logout',           'User Logout'
        OAUTH_LOGIN           = 'oauth_login',           'OAuth Login'
        OAUTH_CONNECTED       = 'oauth_connected',       'OAuth Connected'
        OAUTH_DISCONNECTED    = 'oauth_disconnected',    'OAuth Disconnected'
        MFA_ENABLED           = 'mfa_enabled',           'MFA Enabled'
        MFA_DISABLED          = 'mfa_disabled',          'MFA Disabled'
        MFA_VERIFIED          = 'mfa_verified',          'MFA Verified'
        MFA_FAILED            = 'mfa_failed',            'MFA Failed'
        MFA_BACKUP_USED       = 'mfa_backup_used',       'MFA Backup Code Used'
        DOCUMENT_UPLOADED     = 'document_uploaded',     'Document Uploaded'
        DOCUMENT_DELETED      = 'document_deleted',      'Document Deleted'
        REQUEST_CREATED       = 'request_created',       'Request Created'
        REQUEST_CANCELLED     = 'request_cancelled',     'Request Cancelled'
        TOKEN_GENERATED       = 'token_generated',       'Token Generated'
        TOKEN_ACCESSED        = 'token_accessed',        'Token Accessed'
        TOKEN_EXPIRED         = 'token_expired',         'Token Expired'
        TOKEN_INVALID_ATTEMPT = 'token_invalid_attempt', 'Token Invalid Attempt'
        PRINT_INITIATED       = 'print_initiated',       'Print Initiated'
        PRINT_COMPLETED       = 'print_completed',       'Print Completed'
        PRINT_FAILED          = 'print_failed',          'Print Failed'

    user = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='audit_logs')
    request = models.ForeignKey(PrintRequest,on_delete=models.SET_NULL,null=True,blank=True,related_name='audit_logs')
    action = models.CharField(max_length=50,choices= Action.choices)
    action_detail = models.JSONField(null=True,blank=True)
    ip_address = models.GenericIPAddressField(null=True,blank=True)
    user_agent = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        auditor = self.user.email if self.user else 'System'
        return f"({self.created_at}),  {auditor} - {self.action}"

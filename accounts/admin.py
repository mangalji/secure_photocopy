from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Shops, OTP, MFABackupCode, OAuthConnection, Document, PrintRequest, PrintSession, AuditLogs, Notification

admin.site.register(CustomUser)
admin.site.register(Shops)
admin.site.register(OTP)
admin.site.register(MFABackupCode)
admin.site.register(OAuthConnection)
admin.site.register(AuditLogs)
admin.site.register(Document)
admin.site.register(PrintRequest)
admin.site.register(PrintSession)
admin.site.register(Notification)




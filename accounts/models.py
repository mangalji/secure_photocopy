from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import CustomUserManager
import uuid
from django.utils import timezone



class CustomUser(AbstractBaseUser):

    class Role(models.TextChoices):

        CONSUMER = 'consumer', 'Consumer'
        SHOPKEEPER = 'shopkeeper', 'Shopkeeper'

    class Meta:
        db_table = 'Users'

    user_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15,unique=True)
    role = models.CharField(max_length=50,choices=Role.choices)
    password = models.CharField(max_length=128)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_mfa_enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    address = models.TextField(null=True,blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name','role']


    def __str__(self):
        if self.is_superuser:
            return f"Admin: {self.email}"
        return f"{self.full_name} ({self.email}, {self.phone}, {self.role})"
    
class Shops(models.Model):

    class Meta:
        db_table = 'shops'

    shopkeeper = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='shops')
    shop_name = models.CharField(max_length=100)
    shop_email = models.EmailField(unique=True,null=True)
    shop_phone = models.CharField(max_length=15,unique=True,null=True)
    shop_address = models.TextField()
    city = models.CharField(max_length=100,)
    shop_license_no = models.CharField(max_length=200,unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.shopkeeper},{self.shop_name},{self.city}"

class Document(models.Model):

    class Meta:
        db_table = 'documents'

    consumer = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='documents')
    doc_name = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=20)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True,blank=True)
    file_size_mb = models.DecimalField(max_digits=6,decimal_places=2,null=True,blank=True)
    file_hash = models.CharField(max_length=256)

    def __str__(self):
        return f"{self.doc_name}, {self.consumer.full_name}"

class OTP(models.Model):

    class Purpose(models.TextChoices):

        REGISTRATION = 'registration', 'Registration'
        LOGIN        = 'login',        'Login'
        MFA_SETUP    = 'mfa_setup',    'MFA Setup'
        FORGOT_PASSWORD = 'forgot_password', 'Forgot Password'

    class Meta:
        db_table = 'otp'

    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE, related_name='otp')
    otp_hash = models.CharField(max_length=100)
    purpose = models.CharField(max_length=20,choices=Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True,blank=True)

    
    def __str__(self):
        return f"OTP: {self.user.email} for {self.purpose}"
    
class MFABackupCode(models.Model):

    class Meta:
        db_table = 'mfa_backup_codes'

    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='mfa_backup_code')
    hash_code = models.CharField(max_length=64)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True,blank=True)

    def __str__(self):
        return f"BackUpCode of {self.user.email}, used={self.is_used}"

    
class OAuthConnection(models.Model):

    class Provider(models.TextChoices):
        GOOGLE = 'google', 'Google'
        GITHUB = 'github', 'Github'

    class Meta:
        db_table = 'oauth_connections'

    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='oauth_connection')
    provider = models.CharField(max_length=50,choices=Provider.choices)
    provider_user_id = models.CharField(max_length=255)
    access_token = models.TextField(null=True,blank=True)
    refresh_token = models.TextField(null=True,blank=True)
    token_expires_at = models.DateTimeField(null=True,blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OAuth for {self.user.email}, {self.provider}"
    
class PrintRequest(models.Model):

    class Meta:
        db_table = 'print_requests'

    class Status(models.TextChoices):
        PENDING = 'pending','Pending'
        PRINTING  = 'printing',  'Printing'
        PRINTED   = 'printed',   'Printed'
        EXPIRED   = 'expired',   'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
 
    class PrintColor(models.TextChoices):
        BLACK_WHITE = 'blackwhite','BlackWhite'
        COLOR = 'color','Color'

    
    consumer = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='print_requests_by_consumers')
    shop = models.ForeignKey(Shops,on_delete=models.CASCADE,related_name='print_requests')
    document = models.ForeignKey(Document,on_delete=models.CASCADE,related_name='print_requests')
    status = models.CharField(max_length=20,choices=Status.choices,default=Status.PENDING)
    total_copies = models.PositiveIntegerField(default=1)
    print_color = models.CharField(max_length=20,choices=PrintColor.choices,default=PrintColor.BLACK_WHITE)
    access_token = models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    is_token_used = models.BooleanField(default=False)
    token_expires_at = models.DateTimeField()
    requested_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f" Request by {self.id}, name = {self.consumer.full_name} to {self.shop.shop_name}, current status = {self.status}."
    

class PrintSession(models.Model):
    
    class Meta:
        db_table = 'print_session'

    class SessionStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    request = models.OneToOneField(PrintRequest,on_delete=models.CASCADE,related_name='session')
    shopkeeper = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='print_session')
    document_accessed_at = models.DateTimeField(auto_now_add=True)
    print_initiated_at = models.DateTimeField(null=True,blank=True)
    print_completed_at = models.DateTimeField(null=True,blank=True)
    ip_address = models.GenericIPAddressField(null=True,blank=True)
    user_agent = models.TextField(null=True,blank=True)
    session_status = models.CharField(max_length=20,choices=SessionStatus.choices,default=SessionStatus.ACTIVE)

    def __str__(self):
        return f"session for request: {self.request.id},{self.session_status}."
    

class AuditLogs(models.Model):

    class Meta:
        db_table = 'audit_logs'

    user = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='audit_logs')
    request = models.ForeignKey(PrintRequest,on_delete=models.SET_NULL,null=True,blank=True,related_name='audit_logs')
    action = models.CharField(max_length=20)
    action_detail = models.JSONField(null=True,blank=True)
    ip_address = models.GenericIPAddressField(null=True,blank=True)
    user_agent = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        auditor = self.user.email if self.user else 'System'
        return f"({self.created_at}),  {auditor} - {self.action}"
    

class Notification(models.Model):

    class Meta:
        db_table = 'notifications'

    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='notifications')
    request = models.ForeignKey(PrintRequest,on_delete=models.SET_NULL,null=True,blank=True,related_name='notifications')
    noti_type = models.CharField(max_length=50)
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f" Notification : {self.user.full_name},{self.noti_type},read = {self.is_read}."
    

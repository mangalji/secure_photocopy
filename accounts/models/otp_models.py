from django.db import models
from .auth_models import CustomUser

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
        unique_together = ('user','provider')

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
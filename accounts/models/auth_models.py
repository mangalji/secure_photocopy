from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):

    class Role(models.TextChoices):

        CONSUMER = 'consumer', 'Consumer'
        SHOPKEEPER = 'shopkeeper', 'Shopkeeper'

    class Meta:
        db_table = 'Users'

    user_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15,unique=True)
    address = models.TextField(null=True,blank=True)
    role = models.CharField(max_length=50,choices=Role.choices)
    password = models.CharField(max_length=128)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name','role']


    def __str__(self):
        if self.is_superuser:
            return f"Admin: {self.email}"
        return f"{self.full_name} ({self.email}, {self.phone}, {self.role})"
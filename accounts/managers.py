from django.contrib.auth.models import BaseUserManager

class CustomUserManager(BaseUserManager):
    
    def create_user(self,email,password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not password:
            raise ValueError("Password is required")
        
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active',False)
        extra_fields.setdefault('is_staff',False)
        extra_fields.setdefault('is_superuser',False)

        user = self.model(email=email,**extra_fields)
        user.set_password(password)
        user.save()
        return user
    
    def create_superuser(self,email,password,**extra_fields):
        extra_fields.setdefault('is_active',True)
        extra_fields.setdefault('is_staff',True)
        extra_fields.setdefault('is_superuser',True)
        extra_fields.setdefault('is_email_verified',True)
        if not extra_fields.get('is_staff'):
            raise ValueError("superuser must have is_staff=True")
        if not extra_fields.get('is_superuser'):
            raise ValueError("superuser must have is_superuser = True")
        return self.create_user(email,password,**extra_fields)
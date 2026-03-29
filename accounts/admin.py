from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Shops, Notification

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    list_display = ('user_id','email','full_name','phone','role','is_active','is_email_verified','is_staff')
    list_filter = ('role','is_active','is_email_verified','is_staff','is_superuser')
    search_fields = ('email','full_name','phone')
    ordering = ('-created_at',)

    fieldsets = {
        (None,{'fields':('email','password')}),
    }

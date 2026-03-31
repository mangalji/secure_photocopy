from dataclasses import field
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Shops, Document, PrintRequest, Notification

User = get_user_model()

class RegisterSerializer(serializers.Serializer):

    full_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=15)
    address = serializers.CharField(required=False,allow_blank=True)
    password = serializers.CharField(min_length=8,write_only=True)
    confirm_password = serializers.CharField(min_length=8,write_only=True)
    role = serializers.ChoiceField(choices=User.Role.choices)

    def validate_email(self,value):
        
        if User.objects.filter(email=value,is_active=True).exists():
            raise serializers.ValidationError("this email is already registered with us.")
        
        return value.lower().strip()
    
    def validate_phone(self,value):

        if User.objects.filter(phone=value,is_active=True).exists():
            raise serializers.ValidationError("This phone number is already registered with us.")
        
        return value.strip()
    

    def validate(self,data):

        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password':'passwords do not match.'
            })
        return data
    
    def save(self):
        
        data = self.validated_data

        user = User.objects.create_user(
            full_name = data['full_name'],
            email = data['email'],
            phone = data['phone'],
            address = data['address'],
            password = data['password'],
            role = data['role'],
        )
        return user
    
class VerifyOTPSerializer(serializers.Serializer):

    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6,max_length=6)


class LoginSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class LogoutSerializer(serializers.Serializer):

    refresh_token = serializers.CharField()

class ResendOTPSerializer(serializers.Serializer):

    email = serializers.EmailField()
    purpose = serializers.ChoiceField(choices=['registration','login'])

class ForgotPasswordSerializer(serializers.Serializer):

    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):

    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6,max_length=6)
    new_password = serializers.CharField(min_length=8,write_only=True)
    confirm_new_password = serializers.CharField(min_length=8,write_only=True)

    def validate(self,data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError(
                {'confirm_password':'passwords do not match'}
            )
        return data
    
class ShopsSerializer(serializers.ModelSerializer):
    
    created_at = serializers.DateField(read_only=True,source='created_at.date')
    shopkeeper_name = serializers.CharField(source='shopkeeper.full_name',read_only=True)

    class Meta:
        model = Shops
        fields = [
            'id',
            'shopkeeper_name',
            'shop_name',
            'shop_email',
            'shop_phone',
            'shop_address',
            'city',
            'shop_license_no',
            'is_active',
            'created_at']
        read_only_fields = ['id','is_active','created_at']

class DocumentUploadSerializer(serializers.Serializer):
    
    file = serializers.FileField()

    def validate_file(self,file):
        allowed_types = ['application/pdf','image/jpeg','image/png']
        if file.content_type not in allowed_types:
            raise serializers.ValidationError("only pdfs and images are allowed.") 

        max_size = 100 * 1024 * 1024
        if file.size > max_size:
            raise serializers.ValidationError(
                'file must be not exceeded 100mb.'
            )
            return file

            
class DocumentListSerializer(serializers.ModelSerializer):

    uploaded_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M')

    class Meta:
        model = Document
        fields = ['id','doc_name','doc_type','uploaded_at','file_size_mb','is_deleted',]


class PrintRequestCreateSerializer(serializers.Serializer):

    shop_id = serializers.IntegerField()
    document_id = serializers.IntegerField()
    print_copies = serializers.IntegerField(min_value=1,default=1)
    print_color = serializers.ChoiceField(choices= PrintRequest.PrintColor.choices,default = PrintRequest.PrintColor.BLACK_WHITE)
    expiry_minutes = serializers.ChoiceField(choices=[15,30,60],default = 30)

    def validate_shop(self,value):
        if not Shops.objects.filter(id=value,is_active=True).exists():
            raise serializers.ValidationError('shop not found or inactive')
        return value
    
    def validate_document(self,value):
        if not Document.objects.filter(id=value,is_deleted=False).exists():
            raise serializers.ValidationError("document not found or deleted.")
        return value
    
class PrintRequestListSerializer(serializers.ModelSerializer):

    shop_name = serializers.CharField(source='shop.shop_name', read_only=True)
    document_name = serializers.CharField(source='document.doc_name', read_only=True)
    requested_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M', read_only=True)

    class Meta:
        model = PrintRequest
        fields = [
            'id',
            'shop_name',
            'document_name',
            'status',
            'total_copies',
            'print_color',
            'requested_at',
            'token_expires_at',
            'is_token_used',
        ]


class TokenAccessSerializer(serializers.Serializer):

    access_token = serializers.UUIDField()

class PrintConfirmSerializer(serializers.Serializer):

    session_id = serializers.IntegerField()


class NotificationSerializer(serializers.ModelSerializer):

    request_id = serializers.IntegerField(source='request.id', read_only=True)
    notification_type = serializers.CharField(source='noti_type', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'request_id', 'notification_type', 'title', 'message', 'is_read', 'created_at']


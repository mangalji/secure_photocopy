from accounts.models import CustomUser
from rest_framework import serializers
import re
from django.contrib.auth.password_validation import validate_password

User = CustomUser


class RegisterSerializer(serializers.Serializer):

    full_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=15)
    address = serializers.CharField(required=False,allow_blank=True)
    password = serializers.CharField(min_length=8,write_only=True)
    confirm_password = serializers.CharField(min_length=8,write_only=True)
    role = serializers.ChoiceField(choices=User.Role.choices)

    def validate_full_name(self, value):
        if not re.match(r"^[A-Za-z\s]+$", value):
            raise serializers.ValidationError("Full name can only contain letters and spaces.")
        return value.strip()

    def validate_email(self,value):
        if User.objects.filter(email=value,is_active=True).exists():
            raise serializers.ValidationError("this email is already registered with us.")
        return value.lower().strip()
    
    def validate_phone(self,value):
        if not re.match(r"^\+?1?\d{9,15}$", value):
            raise serializers.ValidationError("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
        if User.objects.filter(phone=value,is_active=True).exists():
            raise serializers.ValidationError("This phone number is already registered with us.")
        return value.strip()

    def validate(self,data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password':'passwords do not match.'
            })
        
        try:
            validate_password(data['password'])
        except Exception as e:
            raise serializers.ValidationError({'password': list(e.messages) if hasattr(e, 'messages') else str(e)})

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


class LoginSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class LogoutSerializer(serializers.Serializer):

    refresh_token = serializers.CharField()
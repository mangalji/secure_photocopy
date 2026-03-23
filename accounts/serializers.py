from rest_framework import serializers
from .models import CustomUser

class RegisterSerializer(serializers.Serializer):

    full_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=15)
    address = serializers.CharField(required=False,allow_blank=True)
    password = serializers.CharField(min_length=8,write_only=True)
    confirm_password = serializers.CharField(min_length=8,write_only=True)
    role = serializers.ChoiceField(choices=CustomUser.Role.choices)

    def check_email(self,value):
        
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("this email is already registered with us.")
        
        return value.lower().strip()
    
    def check_phone(self,value):

        if CustomUser.objects.filter(phone=value).exists():
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

        user = CustomUser.objects.create_user(
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

    
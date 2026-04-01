from rest_framework import serializers
from accounts.models import CustomUser

class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = [
            'full_name',
            'email',
            'phone',
            'address',
            'role',
            'is_email_verified',
            'created_at',
        ]
        read_only_fields = ['email','role','is_email_verified','created_at']

class ProfileUpdateSerializer(serializers.Serializer):

    full_name = serializers.CharField(max_length=50,required=False)
    phone = serializers.CharField(max_length=15,required=False)
    address = serializers.CharField(required=False,allow_blank=True)

    def validate_phone(self,value):
        user = self.context['request'].user
        
        if CustomUser.objects.filter(phone=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('phone no. is already use.')
        
        return value.strip()
    

from rest_framework import serializers
from accounts.models import Shops
import re

class ShopsSerializer(serializers.ModelSerializer):
    
    created_at = serializers.SerializerMethodField()
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
    
    def get_created_at(self,obj):
        return obj.created_at.date().isoformat()
        
    def validate_shop_phone(self, value):
        if value and not re.match(r"^\+?1?\d{9,15}$", value):
            raise serializers.ValidationError("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
        return value.strip() if value else value
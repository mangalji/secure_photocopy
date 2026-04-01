from rest_framework import serializers
from accounts.models import Shops

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
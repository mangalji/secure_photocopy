from rest_framework import serializers
from accounts.models import Shops 
from accounts.models import Document
from accounts.models import PrintRequest

class PrintRequestCreateSerializer(serializers.Serializer):

    shop_id = serializers.IntegerField()
    document_id = serializers.IntegerField()
    print_copies = serializers.IntegerField(min_value=1,default=1)
    print_color = serializers.ChoiceField(choices= PrintRequest.PrintColor.choices,default = PrintRequest.PrintColor.BLACK_WHITE)
    expiry_minutes = serializers.ChoiceField(choices=[15,30,60],default = 30)

    def validate_shop_id(self,value):
        if not Shops.objects.filter(id=value,is_active=True).exists():
            raise serializers.ValidationError('shop not found or inactive')
        return value
    
    def validate_document_id(self,value):
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
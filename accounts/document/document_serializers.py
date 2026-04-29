from rest_framework import serializers 
from accounts.models import Document

class DocumentUploadSerializer(serializers.Serializer):
    
    file = serializers.FileField()

    def validate_file(self,file):
        allowed_types = ['application/pdf','image/jpeg','image/png']
        if file.content_type not in allowed_types:
            raise serializers.ValidationError("only pdfs and images are allowed.") 

        max_size = 10 * 1024 * 1024
        if file.size > max_size:
            raise serializers.ValidationError(
                'file must be not exceeded 10mb.'
            )
        return file
        
class DocumentListSerializer(serializers.ModelSerializer):

    uploaded_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M')

    class Meta:
        model = Document
        fields = ['id','doc_name','doc_type','uploaded_at','file_size_mb','is_deleted',]
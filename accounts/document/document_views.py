from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from accounts.document.document_serializers import DocumentUploadSerializer, DocumentListSerializer
from accounts.models import Document
from rest_framework.response import Response
from rest_framework import status
import hashlib
import secrets
import os
from django.conf import settings
from django.utils import timezone


class DocumentUploadView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):

        if request.user.role != 'consumer':
            return Response(
                {'error':'only consumers can upload the documents.'},
                status = status.HTTP_403_FORBIDDEN
            )

        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,status=status.HTTP_400_BAD_REQUEST
            )

        file = serializer.validated_data['file']

        upload_folder = os.path.join(settings.MEDIA_ROOT,'documents',str(request.user.user_id))
        os.makedirs(upload_folder,exist_ok=True)

        file_path = os.path.join(upload_folder,file.name)

        with open(file_path,'wb+') as location:
            for chunk in file.chunks():
                location.write(chunk)

        sha256 = hashlib.sha256()
        with open(file_path,'rb') as f:
            for chunk in iter(lambda: f.read(8192),b''):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()

        file_size = round(file.size/(1024*1024),2)

        relative_path = os.path.join(
            'documents',str(request.user.user_id),file.name
        )

        document = Document.objects.create(
            consumer = request.user,
            doc_name = file.name,
            doc_type = file.content_type,
            file_hash = file_hash,
            file_size_mb = file_size,
        )

        return Response(
            {
                'message':'document uploaded successfully',
                'document_id':document.id,
                'doc_name':document.doc_name,
                'file_size_mb':document.file_size_mb,
                'doc_type':document.doc_type,
                'uploaded_at':document.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                }, status=status.HTTP_201_CREATED
        )

class DocumentListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request):

        if request.user.role != 'consumer':
            return Response(
                {'error':'onlu consumers can see his documents.'},
                status=status.HTTP_403_FORBIDDEN
            )

        documents = Document.objects.filter(consumer = request.user).order_by('-uploaded_at')

        serializer = DocumentListSerializer(documents,many=True)

        return Response(
            serializer.data,status=status.HTTP_200_OK
        )

class DocumentDeleteView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self,request,document_id):
        try:
            document = Document.objects.get(id=document_id,consumer=request.user)
        except Document.DoesNotExist:
            return Response(
                {'error':'Document not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if document.is_deleted:
            return Response(
                {'error':'document is already deleted.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document.is_deleted = True
        document.deleted_at = timezone.now()
        document.save(update_fields=['is_deleted','deleted_at'])

        return Response(
            {'message':'document deleted successfully.'},
            status=status.HTTP_200_OK
        )
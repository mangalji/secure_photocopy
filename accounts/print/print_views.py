from rest_framework.views import APIView
from accounts.print.print_serializers import (
    PrintRequestCreateSerializer,
    PrintRequestListSerializer,
    PrintConfirmSerializer,
    TokenAccessSerializer
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from accounts.models import PrintRequest, PrintSession
from accounts.models import Shops
from accounts.models import Document
from accounts.models import Notification
from accounts.models import CustomUser
from django.utils import timezone
from datetime import timedelta
from accounts.notification.notification_views import create_notification
import os
from django.conf import settings
from django.db import transaction

User = CustomUser


class PrintRequestCreateView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):

        if request.user.role != 'consumer':
            return Response(
                {'error':"you are not allowed to generate the print request"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PrintRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data

        try:
            document = Document.objects.get(id=data['document_id'],consumer=request.user,is_deleted=False)
        except Document.DoesNotExist:
            return Response(
                {"error":"Document not found or does not belong to you."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        shop = Shops.objects.get(id=data['shop_id'])
        expiry_minutes = data['expiry_minutes']
        token_expires_at = timezone.now() + timedelta(minutes=int(expiry_minutes))

        print_request = PrintRequest.objects.create(
            consumer = request.user,
            shop = shop,
            document = document,
            total_copies = data['print_copies'],
            print_color = data['print_color'],
            token_expires_at = token_expires_at,
            expires_at = token_expires_at,
        )

        create_notification(
            user=request.user,
            request_obj=print_request,
            noti_type=Notification.NotificationType.REQUEST_SENT,
            title='Print request created',
            message=f'Your print request #{print_request.id} has been created and sent to {shop.shop_name}.',
        )

        create_notification(
            user=shop.shopkeeper,
            request_obj=print_request,
            noti_type=Notification.NotificationType.REQUEST_RECEIVED,
            title='New print request received',
            message=f'New print request #{print_request.id} is received from {request.user.full_name}.',
        )

        return Response(
            {
                "message":"Print request created successfully",
                "request_id":print_request.id,
                "access_token":str(print_request.access_token),
                "shop_name":shop.shop_name,
                "document_name":document.doc_name,
                "print_copies": print_request.total_copies,
                "print_color":print_request.print_color,
                "status":print_request.status,
                "token_expires_at":print_request.token_expires_at.strftime('%Y-%m-%d %H:%M'),
            },status=status.HTTP_201_CREATED
        )

class PrintRequestListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request):

        if request.user.role == 'consumer':
            requests = PrintRequest.objects.filter(
                consumer = request.user
            ).order_by("-requested_at")
        elif request.user.role == 'shopkeeper':
            requests = PrintRequest.objects.filter(
                shop__shopkeeper = request.user
            ).order_by('-requested_at')

        else:
            return Response(
                {"error":"unauthorized"},status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PrintRequestListSerializer(requests,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

class PrintRequestCancleView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request,request_id):

        try:
            print_request = PrintRequest.objects.get(
                id = request_id,
                consumer = request.user
            )
        except PrintRequest.DoesNotExist:
            return Response(
                {"error":"print request not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if print_request.status != PrintRequest.Status.PENDING:
            return Response(
                {"error":f"cannot cancle a request with status: {print_request.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print_request.status = PrintRequest.Status.CANCELLED
        print_request.is_token_used = True
        print_request.save(update_fields=['status','is_token_used'])

        return Response(
            {"message":"print request cancelled successfully."},
            status=status.HTTP_200_OK
        )
    
class AccessDocumentView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):

        if request.user.role != 'shopkeeper':
            return Response(
                {"error":"only shopkeepers can access documents."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = TokenAccessSerializer(data=request.data)

        # if token.is_expired():
        #     return Response(
        #         {"error":"your session is expired"},
        #         status=status.HTTP_410_GONE
        #     )

        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        access_token = serializer.validated_data['access_token']

        try:
            print_request = PrintRequest.objects.get(access_token=access_token)
        except PrintRequest.DoesNotExist:
            return Response(
                {"error":"Invalid Token."},
                status=status.HTTP_404_NOT_FOUND
            )
        if print_request.is_token_used:
            return Response(
                {"error":"this token has already been used."},
                status=status.HTTP_403_FORBIDDEN
            )
        if timezone.now() > print_request.token_expires_at:
            print_request.status = PrintRequest.Status.EXPIRED
            print_request.save(update_fields=['status'])
            return Response(
                {"error":"this token has expired."},
                status=status.HTTP_410_GONE
            )
        if print_request.shop.shopkeeper != request.user:
            return Response(
                {"error":"this request does not belong to your shop."},
                status=status.HTTP_403_FORBIDDEN
            )
        with transaction.atomic():

            print_request.is_token_used = True
            print_request.status = PrintRequest.Status.PRINTING
            print_request.save(update_fields=['is_token_used','status'])

            create_notification(
                user=print_request.consumer,
                request_obj=print_request,
                noti_type=Notification.NotificationType.PRINTING,
                title='Print in progress',
                message=f'Your print request #{print_request.id} is being printed by {request.user.full_name}.',
            )

            ip = request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT','')

            session = PrintSession.objects.create(
                request = print_request,
                shopkeeper = request.user,
                ip_address = ip,
                user_agent = ua,
            ) 
            document = print_request.document
            file_path = os.path.join(
                settings.MEDIA_ROOT,
                document.encrypted_storage_ref
            )

            if not os.path.exists(file_path):
                return Response(
                    {"error":"document file not found on server."},
                    status= status.HTTP_404_NOT_FOUND
                )
            
            return Response(
                {
                    "message":"Document accessed successfully.",
                    "session_id":session.id,
                    "doc_name":document.doc_name,
                    "doc_type":document.doc_type,
                    "print_copies":print_request.total_copies,
                    "print_color":print_request.print_color,
                    "file_url":request.build_absolute_uri(
                        settings.MEDIA_URL + document.encrypted_storage_ref
                    ),
                },status=status.HTTP_200_OK
            )

class PrintConfirmView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request,session_id):

        if request.user.role != 'shopkeeper':
            return Response(
                {"error":"only shopkeepers can confirm print."},status=status.HTTP_403_FORBIDDEN
            )
        try:
            session = PrintSession.objects.get(
                id = session_id,
                shopkeeper = request.user
            )
        except PrintSession.DoesNotExist:
            return Response(
                {"error":"print session not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if session.session_status == PrintSession.SessionStatus.COMPLETED:
            return Response(
                {"error":"this session is already comleted."},
                status=status.HTTP_400_BAD_REQUEST
            )
        now = timezone.now()
        session.print_completed_at = now
        session.session_status = PrintSession.SessionStatus.COMPLETED
        session.save(update_fields=['print_completed_at','session_status'])

        print_request = session.request
        print_request.status = PrintRequest.Status.PRINTED
        print_request.save(update_fields=['status'])

        create_notification(
            user=print_request.consumer,
            request_obj=print_request,
            noti_type=Notification.NotificationType.PRINTED,
            title='Print completed',
            message=f'Your print request #{print_request.id} is completed and ready.',
        )
        create_notification(
            user=request.user,
            request_obj=print_request,
            noti_type=Notification.NotificationType.PRINTED,
            title='Print report',
            message=f'Print request #{print_request.id} is marked as completed.',
        )

        document = print_request.document

        file_path = os.path.join(
            settings.MEDIA_ROOT,
            document.encrypted_storage_ref
        )
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        document.is_deleted = True
        document.deleted_at = now
        document.save(update_fields=['is_deleted','deleted_at'])

        return Response(
            {"message":"Print confirmed and document deleted successfully."},
            status=status.HTTP_200_OK
        )

class PrintFailView(APIView):

    permission_classes = [IsAuthenticated]
 
    def post(self, request, session_id):
 
        try:
            session = PrintSession.objects.get(
                id         = session_id,
                shopkeeper = request.user
            )
        except PrintSession.DoesNotExist:
            return Response(
                {'error': 'Print session not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
 
        session.session_status = PrintSession.SessionStatus.FAILED
        session.save(update_fields=['session_status'])
 
        print_request        = session.request
        print_request.status = PrintRequest.Status.CANCELLED
        print_request.save(update_fields=['status'])

        create_notification(
            user=print_request.consumer,
            request_obj=print_request,
            noti_type=Notification.NotificationType.PRINT_FAILED,
            title='Print failed',
            message=f'Your print request #{print_request.id} could not be completed and is cancelled.',
        )
        create_notification(
            user=request.user,
            request_obj=print_request,
            noti_type=Notification.NotificationType.PRINT_FAILED,
            title='Print failed reported',
            message=f'You marked print request #{print_request.id} as failed.',
        )
        
        return Response(
            {'message': 'Print failure reported. Consumer can resend the request.'},
            status=status.HTTP_200_OK
        )
import hashlib
from genericpath import exists
from django.shortcuts import render
import os
import hashlib
import secrets
from datetime import timedelta
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import CustomUser, OTP, Shops, Document, PrintRequest, PrintSession, AuditLogs, Notification
from .serializers import RegisterSerializer, VerifyOTPSerializer, LoginSerializer, LogoutSerializer
from .serializers import ResendOTPSerializer, ResetPasswordSerializer, ForgotPasswordSerializer
from .serializers import ShopsSerializer, DocumentListSerializer, DocumentUploadSerializer
from .serializers import PrintRequestCreateSerializer, PrintRequestListSerializer, TokenAccessSerializer, PrintConfirmSerializer, NotificationSerializer
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.generics import ListAPIView
from django.conf import settings
from django.db import transaction


def create_notification(user, request_obj, noti_type, title, message):
    Notification.objects.create(
        user=user,
        request=request_obj,
        noti_type=noti_type,
        title=title,
        message=message
    )


class RegisterView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):
        
        serializer = RegisterSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)  
        
        email = serializer.validated_data['email']
        phone = serializer.validated_data['phone']
        CustomUser.objects.filter(email=email,is_active=False).delete()
        CustomUser.objects.filter(phone=phone,is_active=False).delete()

        user = serializer.save()

        raw_otp = str(secrets.randbelow(900000)+100000)
        otp_hash = hashlib.sha256(raw_otp.encode('utf-8')).hexdigest()

        OTP.objects.filter(
            user=user,
            purpose = OTP.Purpose.REGISTRATION,
            is_used = False
        ).delete()

        OTP.objects.create(
            user = user,
            otp_hash=otp_hash,
            purpose = OTP.Purpose.REGISTRATION,
            expires_at = timezone.now() + timedelta(minutes=5)
        )

        send_mail(
            subject= 'verify your account',
            message = f'your OTP for registration is: {raw_otp}\n\nThis OTP is valid for only 5 minutes.',
            from_email = 'owner.petwala@gmail.com',
            recipient_list = [user.email],
            fail_silently=False,
        )

        return Response(
            {
                'message':'Registration successfull. OTP sent to your email.',
                'email':user.email,
            },
            status=status.HTTP_201_CREATED
        )
    

class VerifyRegisterOTPView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):

        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"error":"No account found with this email"},status=status.HTTP_404_NOT_FOUND)
        
        if user.is_active:
            return Response({
                "error":"This account is already verified"
            },status=status.HTTP_400_BAD_REQUEST)
        
        otp_hash = hashlib.sha256(otp.encode('utf-8')).hexdigest()

        otp_record = OTP.objects.filter(
            user = user,
            otp_hash = otp_hash,
            purpose = OTP.Purpose.REGISTRATION,
            is_used = False
        ).first()

        if not otp_record:
            return Response(
                {'error':'Invalid OTP'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if timezone.now() > otp_record.expires_at:
            return Response({
                'error':"OTP has expired. Please request a new one."
            },status=status.HTTP_400_BAD_REQUEST)
        
        otp_record.is_used = True
        otp_record.used_at = timezone.now()
        otp_record.save(update_fields=['is_used','used_at'])

        user.is_active = True
        user.is_email_verified = True
        user.save(update_fields=['is_active','is_email_verified'])

        return Response({'message':'email verified successfully, you can now login to your account.'},
                        status=status.HTTP_200_OK)
    

class LoginView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = CustomUser.objects.get(email=email)

        except CustomUser.DoesNotExist:
            return Response(
                {'error':'no account found with this email'},
                status=status.HTTP_404_NOT_FOUND
            )
        if not user.is_active:
            return Response({
                'error':"account is not verified. please verify your email id first."
            },
            status=status.HTTP_400_BAD_REQUEST)
        
        if not user.check_password(password):
            return Response(
                {"error":"Incorrect Password"},status=status.HTTP_400_BAD_REQUEST
            )

        raw_otp = str(secrets.randbelow(900000)+100000)
        otp_hash = hashlib.sha256(raw_otp.encode('utf-8')).hexdigest()

        OTP.objects.filter(
            user = user,
            purpose = OTP.Purpose.LOGIN,
            is_used = False
        ).delete()

        OTP.objects.create(
            user = user,
            otp_hash = otp_hash,
            purpose = OTP.Purpose.LOGIN,
            expires_at = timezone.now() + timedelta(minutes=5)
        )

        send_mail(
            subject= 'verify the otp for login',
            message= f'your otp for login is :{raw_otp}\n\nThis otp is valid for 5 minutes.',
            from_email= None,
            recipient_list=[user.email],
            fail_silently = False,
        )

        return Response({
            'message':'otp sent to your email.',
            'email':user.email,
        },status=status.HTTP_200_OK)
    

class VerifyLoginOTPView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):
        serializer = VerifyOTPSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'No account found with this email.'},
                status=status.HTTP_404_NOT_FOUND)
        
        otp_hash   = hashlib.sha256(otp.encode('utf-8')).hexdigest()
        otp_record = OTP.objects.filter(
            user     = user,
            otp_hash = otp_hash,
            purpose  = OTP.Purpose.LOGIN,
            is_used  = False
        ).first()
        if not otp_record:
            return Response(
                {'error':'invalid otp'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if timezone.now() > otp_record.expires_at:
            return Response(
                {'error':'otp has expired. please login again'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        otp_record.is_used = True
        otp_record.used_at = timezone.now()
        otp_record.save(update_fields=['is_used','used_at'])
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'message':'login successfull',
                'access_token':str(refresh.access_token),
                'refresh_token':str(refresh),
                'user':{
                    'id'        : user.user_id,
                    'full_name' : user.full_name,
                    'email'     : user.email,
                    'role'      : user.role,
                }   
            },status=status.HTTP_200_OK
        )
    
class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):

        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        refresh_token = serializer.validated_data['refresh_token']

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {'error':'Invalid or blacklisted token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {'message':'logged out successfully.'},
            status=status.HTTP_200_OK
        )
    
class ResendOTPView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):

        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        purpose = serializer.validated_data['purpose']

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {'error':'no account find with this mail id.'},
                status=status.HTTP_404_NOT_FOUND
            )
        if purpose == 'registration' and user.is_active:
            return Response(
                {'error':'account is already verified.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if purpose == 'login' and not user.is_active:
            return Response(
                {'error':'account is not verified yet.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        OTP.objects.filter(
            user = user,
            purpose = purpose,
            is_used = False
        ).delete()

        raw_otp = str(secrets.randbelow(900000)+100000)
        otp_hash = hashlib.sha256(raw_otp.encode('utf-8')).hexdigest()

        OTP.objects.create(
            user = user,
            otp_hash = otp_hash,
            purpose = purpose,
            expires_at = timezone.now() + timedelta(minutes=5)
        )

        send_mail(
            subject= 'verify resend otp',
            message = f'Your new OTP is: {raw_otp}\n\nThis OTP is valid for 5 minutes.',
            from_email = None,
            recipient_list= [user.email],
            fail_silently= False,
        )

        return Response(
            {'message':'otp resent successfully.',
             'email':user.email,},
             status=status.HTTP_200_OK
        )
    
class ForgotPasswordView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):
        serializer = ForgotPasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {'error':'no account found with this mail.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not user.is_active:
            return Response(
                {'error':'account is not verified. please verify your email firstly.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        OTP.objects.filter(
            user = user,
            purpose = OTP.Purpose.FORGOT_PASSWORD,
            is_used = False
        ).delete()

        raw_otp = str(secrets.randbelow(900000)+100000)
        otp_hash = hashlib.sha256(raw_otp.encode('utf-8')).hexdigest()

        OTP.objects.create(
            user = user,
            otp_hash = otp_hash,
            purpose = OTP.Purpose.FORGOT_PASSWORD,
            expires_at = timezone.now() + timedelta(minutes=5)
        )

        send_mail(
            subject= 'verify otp for forgot password',
            message = f'your otp for reset the password is{raw_otp}\n\nThis OTP is valid for 5 minutes.',
            from_email= None,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response(
            {'message':'password reset otp sent to your email.',
             'email':user.email},
             status=status.HTTP_200_OK
        )
    
class ResetPasswordView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {'error':'no account found with this email.'},
                status=status.HTTP_404_NOT_FOUND
            )
        otp_hash = hashlib.sha256(otp.encode('utf-8')).hexdigest()
        otp_record = OTP.objects.filter(
            user = user,
            otp_hash = otp_hash,
            purpose = OTP.Purpose.FORGOT_PASSWORD,
            is_used = False,
        ).first()

        if not otp_record:
            return Response(
                {'error':'invalid otp'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if timezone.now() > otp_record.expires_at:
            return Response(
                {'error':'otp has expired. please request for new otp.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        otp_record.is_used = True
        otp_record.used_at = timezone.now()
        otp_record.save(update_fields=['is_used','used_at'])
        user.set_password(new_password)
        user.save(update_fields=['password'])

        return Response(
            {'message':'password reset successfully. you can now login.'},
            status=status.HTTP_200_OK
        )

class ShopRegisterView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):
        user = request.user

        if user.role != CustomUser.Role.SHOPKEEPER:
            return Response(
                {'error':'only shopkeepers can register in shops'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = ShopsSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,status=status.HTTP_400_BAD_REQUEST
                )
        serializer.save(shopkeeper=user)
        
        return Response(
            {
                'message':'shop registered successfully',
                'shop': serializer.data,
            }
            ,status=status.HTTP_201_CREATED
        )
    
class ShopListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request):
        shops = Shops.objects.filter(is_active=True)
        city = request.query_params.get('city')
        if city:
            shops = shops.filter(city__icontains=city)
        
        serializer = ShopsSerializer(shops,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    
class ShopDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request,shop_id):
        try:
            shop = Shops.objects.get(id=shop_id,is_active=True)
        except Shops.DoesNotExist:
            return Response(
                {'error':'shop not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ShopsSerializer(shop)
        return Response(
            serializer.data,status=status.HTTP_200_OK
        )
    
class ShopUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self,request,shop_id):
        try:
            shop = Shops.objects.get(id=shop_id)
        except Shops.DoesNotExist:
            return Response(
                {'error':'shop not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        if shop.shopkeeper != request.user:
            return Response(
                {'error':'you are not the owner of this shop.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = ShopsSerializer(shop,data=request.data,partial=True)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save()
        return Response(
            {'message':'shop updated successfully',
             'shop':serializer.data,},
             status=status.HTTP_200_OK
        )
    
class ShopDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self,request,shop_id):
        try:
            shop = Shops.objects.get(id=shop_id)
        except Shops.DoesNotExist:
            return Response(
                {'error':'shop not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        if shop.shopkeeper != request.user:
            return Response(
                {'error':'you are not the owner of this shop.'},
                status=status.HTTP_403_FORBIDDEN
            )
        shop.is_active = False
        shop.save(update_fields=['is_active'])

        return Response(
            {'message':'shop deleted successfully.'},
            status=status.HTTP_200_OK
        )

class DocumentUploadView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):

        # if request.user.role != 'consumer':
        #     return Response(
        #         {'error':'only consumers can upload the documents.'},
        #         status = status.HTTP_403_FORBIDDEN
        #     )

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
            print_copies = data['print_copies'],
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

    def post(self,request):

        request_id = request.data.get('request_id')
        if not request_id:
            return Response(
                {'error':'request_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
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
                user=request.user,
                request_obj=print_request,
                noti_type=Notification.NotificationType.PRINTING,
                title='Print started',
                message=f'You started printing request #{print_request.id}.',
            )
            create_notification(
                user=print_request.consumer,
                request_obj=print_request,
                noti_type=Notification.NotificationType.PRINTING,
                title='Print in progress',
                message=f'Your print request #{print_request.id} is being printed by {request.user.full_name}.',
            )

            ip = (request.META.get('HTTP_X_FORWARDED_FOR','').split(',')[0].strip() or request.META.get('REMOTE_ADDR'))
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
            os.remove(file_path)

        document.is_deleted = True
        document.deleted_at = now
        document.save(update_fields=['is_deleted','deleted_at'])

        return Response(
            {"message":"print condirmed, document deleted successfully"},
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

class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notification_id = request.data.get('notification_id')
        if not notification_id:
            return Response({'error': 'notification_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
        except Notification.DoesNotExist:
            return Response({'error': 'notification not found.'}, status=status.HTTP_404_NOT_FOUND)

        notification.is_read = True
        notification.save(update_fields=['is_read'])

        return Response({'message': 'notification marked as read.'}, status=status.HTTP_200_OK)    
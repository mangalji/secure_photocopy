from rest_framework.permissions import AllowAny, IsAuthenticated
from accounts.otp.otp_serializers import VerifyOTPSerializer, ResendOTPSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.models import CustomUser
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from accounts.models import OTP
import hashlib
import secrets
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail

User = CustomUser

class VerifyRegisterOTPView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):

        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
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

class VerifyLoginOTPView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):
        serializer = VerifyOTPSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
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
    
class ResendOTPView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):

        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        purpose = serializer.validated_data['purpose']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
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
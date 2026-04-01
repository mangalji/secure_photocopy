from rest_framework.views import APIView
from accounts.password.resetpassword_serializers import ForgotPasswordSerializer, ResetPasswordSerializer, ChangePasswordSerializer
from accounts.models import OTP
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import secrets 
import hashlib
from django.core.mail import send_mail

User = get_user_model()

class ForgotPasswordView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):
        serializer = ForgotPasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
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
            user = User.objects.get(email=email)
        except User.DoesNotExist:
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
    
class ChangePasswordView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):

        serializer = ChangePasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        user = request.user

        if not user.check_password(data['current_password']):
            return Response(
                {"error":"current pasword didn't match in our records."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(data['new_password'])
        user.save(update_fields=['password'])

        return Response(
            {"message":"password changed successfully. please login again."},
            status=status.HTTP_200_OK
        )
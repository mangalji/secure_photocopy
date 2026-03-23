from django.shortcuts import render

import hashlib
import secrets
from datetime import timedelta
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import CustomUser, OTP
from .serializers import RegisterSerializer, VerifyOTPSerializer

class RegisterView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):
        
        serializer = RegisterSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)  
        
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
            from_email = None,
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
            return Response({"error":"No account found with this email"},)
        
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
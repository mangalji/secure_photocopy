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
from .serializers import RegisterSerializer

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
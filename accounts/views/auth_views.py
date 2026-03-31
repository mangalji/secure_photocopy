from accounts.models import Shops, OTP
from django.contrib.auth import get_user_model
from accounts.serializers import RegisterSerializer, LoginSerializer, LogoutSerializer
from rest_framework.views import APIView
from django.core.mail import send_mail
import secrets
import hashlib
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


User = get_user_model()

class RegisterView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):
        
        serializer = RegisterSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)  
        
        email = serializer.validated_data['email']
        phone = serializer.validated_data['phone']
        User.objects.filter(email=email,is_active=False).delete()
        User.objects.filter(phone=phone,is_active=False).delete()

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

class LoginView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(email=email)

        except User.DoesNotExist:
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
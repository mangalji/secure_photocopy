from django.shortcuts import render

import hashlib
import secrets
from datetime import timedelta
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import CustomUser, OTP
from .serializers import RegisterSerializer, VerifyOTPSerializer, LoginSerializer, LogoutSerializer
from .serializers import ResendOTPSerializer, ResetPasswordSerializer, ForgotPasswordSerializer
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

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
        
        if purpose == 'login' and user.is_active:
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
            recipient_list=['user.email'],
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
    
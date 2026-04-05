from rest_framework.views import APIView
import pyotp
import qrcode
import base64
from io import BytesIO
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from accounts.models import MFABackupCode
import hashlib
import secrets
from .serializers import MFAVerifySerializer, MFALoginSerializer
from accounts.models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken

User = CustomUser

class MFASetupView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request):
        user = request.user

        if user.mfa_enabled:
            return Response(
                {"error":"MFA is already enabled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.save(update_fields=['mfa_secret'])

        totp_uri = pyotp.TOTP(secret).provisioning_uri(name=user.email,issuer_name='SecureDocument')
        qr_image = qrcode.make(totp_uri)
        buffer = BytesIO()
        qr_image.save(buffer,format='PNG')
        qr_base_64 = base64.b64encode(buffer.getvalue()).decode()

        return Response(
            {
                "message":"scan this qr with google authenticator.",
                "secret":secret,
                "qr_code":f"data:image/png;base64,{qr_base_64}",
                "next_step":"submit the 6 digit code from google authenticator on two factor authentication setup page."
            },
            status=status.HTTP_200_OK
        )
    
class MFAEnableView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):

        serializer = MFAVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        totp_code = serializer.validated_data['totp_code']

        if not user.mfa_secret:
            return Response(
                {"error":"please setup two factor authentication first via two step verification setup page."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(totp_code):
            return Response(
                {"error":"invalid/expired otp"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.mfa_enabled = True
        user.save(update_fields=['mfa_enabled'])
        
        MFABackupCode.objects.filter(user=user).delete()
        raw_codes = []

        for _ in range(8):
            raw_code = secrets.token_hex(4).upper()
            code_hash = hashlib.sha256(raw_code.encode()).hexdigest()
            MFABackupCode.objects.create(user=user,code_hash=code_hash)
            raw_codes.append(raw_code)
        
        return Response(
            {
                "message":"two step verfication setup successfully.",
                "backup_codes":raw_codes,
                "warning":"save these backup codes, they never show again."
            },
            status=status.HTTP_200_OK
        )
    
class MFADisableView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):

        serializer = MFAVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        totp_code = serializer.validated_data['totp_code']
        
        if not user.mfa_enabled:
            return Response(
                {"error":"two step verification is not enable, first setup it."},
                status=status.HTTP_400_BAD_REQUEST
            )
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(totp_code):
            return Response(
                {"error":"invalid code."},status=status.HTTP_400_BAD_REQUEST
            )
        user.mfa_enabled = False
        user.mfa_secret = None
        user.save(update_fields=['mfa_enabled','mfa_secret'])

        MFABackupCode.objects.filter(user=user).delete()

        return Response(
            {"message":"two step verification disabled successfully"},
            status=status.HTTP_200_OK
        )
    
class MFALoginVerifyView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):

        serializer = MFALoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        totp_code = serializer.validated_data['totp_code']

        try:
            user = User.objects.get(email=email,is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error":"user not found."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not user.mfa_enabled:
            return Response(
                {"error":"two step verification is not enabled for this account."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(totp_code):
            return Response(
                {"error":"invalid code"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message":"two step code verified. Login successful.",
                "access_token":str(refresh.access_token),
                "refresh_token":str(refresh),
                "user":{
                    'id':user.user_id,
                    "full_name":user.full_name,
                    "email":user.email,
                    "role":user.role,
                }
            },
            status=status.HTTP_200_OK
        )


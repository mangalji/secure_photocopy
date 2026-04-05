from rest_framework import serializers
from accounts.models.otp_models import MFABackupCode

class MFAVerifySerializer(serializers.Serializer):

    totp_code = serializers.CharField(min_length=6,max_length=6)

class MFALoginSerializer(serializers.Serializer):

    email = serializers.EmailField()
    totp_code = serializers.CharField(min_length=6,max_length=6)


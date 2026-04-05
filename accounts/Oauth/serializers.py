from rest_framework import serializers
from accounts.models.otp_models import OAuthConnection

class OAuthGoogleSerializer(serializers.Serializer):
    
    code = serializers.CharField()
    redirect_url = serializers.CharField()


class OAuthGithubSerializer(serializers.Serializer):

    code = serializers.CharField()
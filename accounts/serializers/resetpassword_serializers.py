from rest_framework import serializers 

class ForgotPasswordSerializer(serializers.Serializer):

    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):

    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6,max_length=6)
    new_password = serializers.CharField(min_length=8,write_only=True)
    confirm_new_password = serializers.CharField(min_length=8,write_only=True)

    def validate(self,data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError(
                {'confirm_password':'passwords do not match'}
            )
        return data
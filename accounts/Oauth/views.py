from rest_framework.views import APIView
import requests
from django.conf import settings
from rest_framework.permissions import AllowAny
from .serializers import OAuthGoogleSerializer, OAuthGithubSerializer
from accounts.models import OAuthConnection
from rest_framework.response import Response
from rest_framework import status
from accounts.models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken

User = CustomUser

class OAuthGoogleView(APIView):

    """
    flow:
    
    1. frontend redirects user to google consent screen.
    2. google redirects back with ?code=...
    3. frontend sends that code here.
    4. backend exchange code for google user info.
    5. user created or fetched, jwt returned.
    """

    permission_classes = [AllowAny]

    def post(self,request):
        serializer = OAuthGoogleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code']
        redirect_uri = serializer.validated_data['redirect_uri']

        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code':code,
                'client_id':'client_id',
                'client_secret':'client secret',
                'redirect_uri':redirect_uri,
                'grant_type':'auth_code',
            }
        )
        if token_response.status_code != 200:
            return Response(
                {"error":"failed to exchange code with google."},
                status=status.HTTP_400_BAD_REQUEST
            )
        token_data = token_response.json()
        access_token = token_data.get('access_token')

        user_info_response = request.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers = {'Authorization':f'Bearer {access_token}'}
        )

        if user_info_response.status_code != 200:
            return Response(
                {"error":'failed to get user info from google.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user_info = user_info_response.json()
        google_id = user_info.get('id')
        email = user_info.get('email')
        full_name = user_info.get('name','')

        oauth_connection = OAuthConnection.objects.filter(
            provider = OAuthConnection.Provider.GOOGLE,
            provider_user_id = google_id
        ).first()

        if oauth_connection:
            user = oauth_connection.user
            oauth_connection.access_token = access_token
            oauth_connection.save(update_fields=['access_token','upload_at'])
        else:
            user = User.objects.filter(email=email).first()

            if not user:
                user = User.objects.create(
                    email = email,
                    full_name = full_name,
                    role = User.Role.CONSUMER,
                    is_active = True,
                    is_email_verified = True,
                )
                user.set_unusable_password()
                user.save()
            OAuthConnection.objects.create(
                user=user,
                provider = OAuthConnection.Provider.GOOGLE,
                provider_user_id = google_id,
                access_token = access_token,

            )
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message":"google login successfull",
                "access_token":str(refresh.access_token),
                "refresh_token":str(refresh),
                "user":{
                    "id":user.user_id,
                    "full_name":user.full_name,
                    "email":user.email,
                    "role":user.role,
                }
            },
            status=status.HTTP_200_OK
        )

class OAuthGithubLoginView(APIView):

    permission_classes = [AllowAny]

    def post(self,request):
        serializer = OAuthGithubSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        code = serializer.validated_data['code']

        token_response = request.post(
            'https://github.com/login/oauth/access_token',
            headers = {'Accept':'application/json'},
            data={
                'client_id': settings.GITHUB_CLIENT_ID,
                'client_secret':settings.GITHUB_CLIENT_SECRET,
                'code':code,
            }
        )
        token_data = token_response.json()
        access_token = token_data.get('access_token')

        if not access_token:
            return Response(
                {"error":"failed to get the token from github"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_info = requests.get(
            'https://api.github.com/user',
            headers={'Authorization':f'Bearer {access_token}'}
        ).json()

        emails = requests.get(
            'https://api.github.com/user/emails',
            headers={'Authorization':f'Bearer {access_token}'}
        ).json()

        primary_email = next(
            (e['email'] for e in emails if e.get('primary') and e.get('verified')),None
        )

        if not primary_email:
            return Response(
                {"error":"no verified email found on GitHub account."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        github_id = str(user_info.get('id'))
        full_name = user_info.grt('name') or user_info.get('login','')

        oauth_connection = OAuthConnection.objects.filter(
            provider = OAuthConnection.Provider.GITHUB,
            provider_user_id = github_id
        ).first()

        if oauth_connection:
            user = oauth_connection.user
            oauth_connection.access_token = access_token
            oauth_connection.save(update_fields=['access_token','updated_at'])
        else:
            user = User.objects.filter(email=primary_email).first()
            if not user:
                user = User.objects.create(
                    email = primary_email,
                    full_name = full_name,
                    role = User.Role.CONSUMER,
                    is_active = True,
                    is_email_verified = True,
                )
                user.set_unusable_password()
                user.save()
            
            OAuthConnection.objects.create(
                user = user,
                provider = OAuthConnection.Provider.GITHUB,
                provider_user_id = github_id,
                access_token = access_token,
            )
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message":"github login successfully",
                "access_token":str(refresh.access_token),
                "refresh_token":str(refresh),
                "user":{
                    "id":user.user_id,
                    "full_name":user.full_name,
                    "email":user.email,
                    "role":user.role,
                }
            },
            status=status.HTTP_200_OK
        )
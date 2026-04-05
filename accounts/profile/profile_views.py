from rest_framework.views import APIView
from accounts.profile.profile_serializers import ProfileSerializer, ProfileUpdateSerializer
from rest_framework import status
from rest_framework.response import Response
from accounts.models import CustomUser
from rest_framework.permissions import IsAuthenticated

User = CustomUser

class ProfileView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request):

        serializer = ProfileSerializer(data=request.user)
        return Response(serializer.errors,status=status.HTTP_200_OK)

class ProfileUpdateView(APIView):

    permission_classes = [IsAuthenticated]

    def put(self,request):

        serializer = ProfileUpdateSerializer(data=request.data,context={"request":request})

        if not serializer.is_valid():
            return Response(
                serializer.errors,status=status.HTTP_400_BAD_REQUEST
            )
        data = serializer.validated_data
        user = request.user

        if 'full_name' in data:
            user.full_name = data['full_name']
        
        if 'phone' in data:
            user.phone = data['phone']
        
        if 'address' in data:
            user.address = data['address']

        user.save()

        return Response(
            {"message":"profile updated successfully.",
             "user":ProfileSerializer(user).data,},
             status=status.HTTP_200_OK
        )

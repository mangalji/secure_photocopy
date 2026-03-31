from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from accounts.serializers.shop_serializers import ShopsSerializer
from accounts.models import Shops
from rest_framework import status
from rest_framework.response import Response


User = get_user_model()

class ShopRegisterView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):
        user = request.user

        if user.role != User.Role.SHOPKEEPER:
            return Response(
                {'error':'only shopkeepers can register in shops'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = ShopsSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,status=status.HTTP_400_BAD_REQUEST
                )
        serializer.save(shopkeeper=user)
        
        return Response(
            {
                'message':'shop registered successfully',
                'shop': serializer.data,
            }
            ,status=status.HTTP_201_CREATED
        )
    
class ShopListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request):
        shops = Shops.objects.filter(is_active=True)
        city = request.query_params.get('city')
        if city:
            shops = shops.filter(city__icontains=city)
        
        serializer = ShopsSerializer(shops,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    
class ShopDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request,shop_id):
        try:
            shop = Shops.objects.get(id=shop_id,is_active=True)
        except Shops.DoesNotExist:
            return Response(
                {'error':'shop not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ShopsSerializer(shop)
        return Response(
            serializer.data,status=status.HTTP_200_OK
        )
    
class ShopUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self,request,shop_id):
        try:
            shop = Shops.objects.get(id=shop_id)
        except Shops.DoesNotExist:
            return Response(
                {'error':'shop not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        if shop.shopkeeper != request.user:
            return Response(
                {'error':'you are not the owner of this shop.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = ShopsSerializer(shop,data=request.data,partial=True)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save()
        return Response(
            {'message':'shop updated successfully',
             'shop':serializer.data,},
             status=status.HTTP_200_OK
        )
    
class ShopDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self,request,shop_id):
        try:
            shop = Shops.objects.get(id=shop_id)
        except Shops.DoesNotExist:
            return Response(
                {'error':'shop not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        if shop.shopkeeper != request.user:
            return Response(
                {'error':'you are not the owner of this shop.'},
                status=status.HTTP_403_FORBIDDEN
            )
        shop.is_active = False
        shop.save(update_fields=['is_active'])

        return Response(
            {'message':'shop deleted successfully.'},
            status=status.HTTP_200_OK
        )
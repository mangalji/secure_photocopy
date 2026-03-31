from rest_framework.views import APIView
from accounts.models import Notification
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from accounts.serializers import NotificationSerializer

def create_notification(user, request_obj, noti_type, title, message):
    Notification.objects.create(
        user=user,
        request=request_obj,
        noti_type=noti_type,
        title=title,
        message=message
    )
    
    

class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notification_id = request.data.get('notification_id')
        if not notification_id:
            return Response({'error': 'notification_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
        except Notification.DoesNotExist:
            return Response({'error': 'notification not found.'}, status=status.HTTP_404_NOT_FOUND)

        notification.is_read = True
        notification.save(update_fields=['is_read'])

        return Response({'message': 'notification marked as read.'}, status=status.HTTP_200_OK)
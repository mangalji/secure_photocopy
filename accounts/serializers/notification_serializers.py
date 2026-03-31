from rest_framework import serializers
from accounts.models import Notification

class NotificationSerializer(serializers.ModelSerializer):

    request_id = serializers.IntegerField(source='request.id', read_only=True)
    notification_type = serializers.CharField(source='noti_type', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'request_id', 'notification_type', 'title', 'message', 'is_read', 'created_at']


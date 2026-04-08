from rest_framework import serializers
from accounts.models import AuditLogs

class AuditLogSerializer(serializers.ModelSerializer):

    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M', read_only=True)

    class Meta:

        model = AuditLogs
        fields = ['id','action','action_detail','ip_address','created_at']
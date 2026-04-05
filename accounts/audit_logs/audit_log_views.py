from rest_framework.views import APIView
from accounts.models import AuditLogs
from .audit_log_serializers import AuditLogSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

class AuditLogListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request):
        
        logs = AuditLogs.objects.filter(
            user=request.user
        ).order_by('-created_at')[:50]

        serializer = AuditLogSerializer(logs,many=True)

        return Response(serializer.errors,status=status.HTTP_200_OK)
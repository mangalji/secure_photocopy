from django.db import models
from .auth_models import CustomUser
from .print_models import PrintRequest

class Notification(models.Model):

    class Meta:
        db_table = 'notifications'

    class NotificationType(models.TextChoices):
        REQUEST_RECEIVED = 'request_received', 'Print Request Received'
        REQUEST_SENT     = 'request_sent',     'Print Request Sent'
        PRINTING         = 'printing',         'Document Being Printed'
        PRINTED          = 'printed',          'Document Printed'
        EXPIRED          = 'expired',          'Request Expired'
        CANCELLED        = 'cancelled',        'Request Cancelled'
        DOCUMENT_DELETED = 'document_deleted', 'Document Deleted'
        PRINT_FAILED     = 'print_failed',     'Print Failed'

    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='notifications')
    request = models.ForeignKey(PrintRequest,on_delete=models.SET_NULL,null=True,blank=True,related_name='notifications')
    noti_type = models.CharField(max_length=50, choices=NotificationType.choices)
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f" Notification : {self.user.full_name},{self.noti_type},read = {self.is_read}."
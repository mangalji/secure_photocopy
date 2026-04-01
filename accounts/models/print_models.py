from django.db import models 
from .auth_models import CustomUser
from .document_models import Document
from .shop_models import Shops
import uuid

class PrintRequest(models.Model):

    class Meta:
        db_table = 'print_requests'

    class Status(models.TextChoices):
        PENDING = 'pending','Pending'
        PRINTING  = 'printing',  'Printing'
        PRINTED   = 'printed',   'Printed'
        EXPIRED   = 'expired',   'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
 
    class PrintColor(models.TextChoices):
        BLACK_WHITE = 'blackwhite','BlackWhite'
        COLOR = 'color','Color'

    
    consumer = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='print_requests_by_consumers')
    shop = models.ForeignKey(Shops,on_delete=models.CASCADE,related_name='print_requests')
    document = models.ForeignKey(Document,on_delete=models.CASCADE,related_name='print_requests')
    status = models.CharField(max_length=20,choices=Status.choices,default=Status.PENDING)
    total_copies = models.PositiveIntegerField(default=1)
    print_color = models.CharField(max_length=20,choices=PrintColor.choices,default=PrintColor.BLACK_WHITE)
    access_token = models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    is_token_used = models.BooleanField(default=False)
    token_expires_at = models.DateTimeField()
    requested_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f" Request by {self.id}, name = {self.consumer.full_name} to {self.shop.shop_name}, current status = {self.status}."
    
class PrintSession(models.Model):
    
    class Meta:
        db_table = 'print_session'

    class SessionStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    request = models.OneToOneField(PrintRequest,on_delete=models.CASCADE,related_name='session')
    shopkeeper = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='print_session')
    document_accessed_at = models.DateTimeField(auto_now_add=True)
    print_initiated_at = models.DateTimeField(null=True,blank=True)
    print_completed_at = models.DateTimeField(null=True,blank=True)
    ip_address = models.GenericIPAddressField(null=True,blank=True)
    user_agent = models.TextField(null=True,blank=True)
    session_status = models.CharField(max_length=20,choices=SessionStatus.choices,default=SessionStatus.ACTIVE)

    def __str__(self):
        return f"session for request: {self.request.id},{self.session_status}."
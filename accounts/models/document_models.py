from django.db import models
from .auth_models import CustomUser

class Document(models.Model):

    class Meta:
        db_table = 'documents'

    consumer = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='documents')
    doc_name = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=20)
    encrypted_storage_ref = models.CharField(max_length=500)
    encryption_key_ref = models.CharField(max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True,blank=True)
    file_size_mb = models.DecimalField(max_digits=6,decimal_places=2,null=True,blank=True)
    file_hash = models.CharField(max_length=256)

    def __str__(self):
        return f"{self.doc_name}, {self.consumer.full_name}"
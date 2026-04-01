from django.db import models 
from .auth_models import CustomUser

class Shops(models.Model):

    class Meta:
        db_table = 'shops'

    shopkeeper = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='shops')
    shop_name = models.CharField(max_length=100)
    shop_email = models.EmailField(unique=True,null=True)
    shop_phone = models.CharField(max_length=15,unique=True,null=True)
    shop_address = models.TextField()
    city = models.CharField(max_length=100,)
    shop_license_no = models.CharField(max_length=200,unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.shopkeeper},{self.shop_name},{self.city}"
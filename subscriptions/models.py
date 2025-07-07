from django.db import models

from areas.models import Area, PostalCode
from products.models import Product

class Box(models.Model):
    name = models.CharField(max_length=100)
    items =  models.ManyToManyField(Product)
    def __str__(self):
        return self.name

from django.core.exceptions import ObjectDoesNotExist

class FreeBoxRequest(models.Model):
    number_of_people = models.IntegerField()
    date_of_delivery = models.DateField()
    box = models.ForeignKey(
        Box, on_delete=models.CASCADE, related_name='requests')
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    postal_code = models.CharField(max_length=10)
    address = models.CharField(max_length=255)
    area_name = models.ForeignKey(
        Area, on_delete=models.CASCADE, blank=True, null=True)
    email = models.EmailField()
    message = models.TextField()
    delivery_status = models.BooleanField(default=False, blank=True, null=True)
    create_at = models.DateField(auto_now=True,blank=True, null=True)
    

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Automatically set the area based on the postal code
        if self.postal_code:  # Ensure postal_code is provided
            try:
                postal_code_instance = PostalCode.objects.get(code=self.postal_code)
                self.area_name = postal_code_instance.area
            except PostalCode.DoesNotExist:
                self.area_name = None  # or you can leave it as None if no area found
        super().save(*args, **kwargs)

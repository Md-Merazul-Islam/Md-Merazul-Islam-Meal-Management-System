
from django.db import models
from django.utils.text import slugify
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:  
            old_category = Category.objects.get(pk=self.pk)
            if old_category.name != self.name:
                self.slug = slugify(self.name)
        else:  
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class Product(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    main_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.CharField(max_length=300, blank=True, null=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.price and self.main_price:
            self.revenue = self.price - self.main_price
        super(Product, self).save(*args, **kwargs)

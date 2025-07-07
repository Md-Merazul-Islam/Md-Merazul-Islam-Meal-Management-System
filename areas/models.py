from django.db import models
from django.utils.text import slugify
from django.contrib.auth import get_user_model
User = get_user_model()
class Area(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    def save(self, *args, **kwargs):
        
        original_slug = slugify(self.name)

        
        if not self.pk:  
            self.slug = original_slug
        else:
            
            old_category = Area.objects.get(pk=self.pk)
            if old_category.name != self.name:
                self.slug = original_slug
            else:
                self.slug = original_slug

        
        counter = 1
        unique_slug = self.slug
        while Area.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{original_slug}-{counter}"
            counter += 1

        self.slug = unique_slug

        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PostalCode(models.Model):
    code = models.CharField(max_length=10, unique=True)
    area = models.ForeignKey(
        Area, related_name='postal_codes', on_delete=models.CASCADE)

    def __str__(self):
        return self.code


class DeliveryManArea(models.Model):
    delivery_man =models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, blank=True, null=True)
    create_at = models.DateField(auto_now=True)
    average_rating = models.FloatField(default=0.0,blank=True, null=True)
    
    def __str__(self):
        return f"Delivery area forarea" 

    def update_average_rating(self):
        """Calculate and update the average rating."""
        reviews = Review.objects.filter(delivery_man=self)
        if reviews.exists():
            total_rating = sum([review.rating for review in reviews])
            self.average_rating = total_rating / reviews.count()
            self.save()


class Review(models.Model):
    delivery_man = models.ForeignKey(DeliveryManArea, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)  
    rating = models.PositiveIntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])  
    review_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review for {self.delivery_man.delivery_man} by {self.user}'

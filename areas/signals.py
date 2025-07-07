from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Review, DeliveryManArea

@receiver(post_save, sender=Review)
def update_average_rating_on_create(sender, instance, created, **kwargs):
    if created:
        instance.delivery_man.update_average_rating()

@receiver(post_delete, sender=Review)
def update_average_rating_on_delete(sender, instance, **kwargs):
    instance.delivery_man.update_average_rating()

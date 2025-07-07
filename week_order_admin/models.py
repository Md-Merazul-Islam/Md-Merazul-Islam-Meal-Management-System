from django.db import models
from weekly_order_manage.models import Payment, OrderShippingAddress, Order, DeliveryDay, DeliveryItem, DeliveryWeek
from django.contrib.auth import get_user_model
User = get_user_model()
# delivery day cancel request send by admin


class CancelDelivery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    delivery_day = models.ForeignKey(DeliveryDay, on_delete=models.CASCADE)
    reason = models.TextField()
    request_status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.delivery_day}"
      
      

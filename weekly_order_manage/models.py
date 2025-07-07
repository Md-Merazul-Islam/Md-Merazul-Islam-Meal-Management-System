from django.db import models
from django.contrib.auth import get_user_model
import uuid
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.core.validators import MinValueValidator
from products.models import Product
from areas.models import Area

User = get_user_model()


class OrderShippingAddress(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='shipping_addresses')
    shipping_address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    area = models.ForeignKey(
        Area, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Order Shipping Addresses"

    def __str__(self):
        return f"{self.user.username}'s shipping address"


class StripeCustomer(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='weekly_stripe_customer')
    stripe_customer_id = models.CharField(max_length=255, unique=True)
    default_payment_method_id = models.CharField(
        max_length=255, blank=True, null=True)
    card_last_four = models.CharField(max_length=4, blank=True, null=True)
    card_brand = models.CharField(max_length=20, blank=True, null=True)
    card_exp_month = models.IntegerField(null=True, blank=True)
    card_exp_year = models.IntegerField(null=True, blank=True)
    is_card_valid = models.BooleanField(default=True)
    stripe_subscription_id = models.CharField(
        max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Stripe Customer: {self.user.username}"


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )

    SUBSCRIPTION_TYPE_CHOICES = (
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )

    SUBSCRIPTION_DURATION_CHOICES = (
        (1, '1 Month'),
        (3, '3 Months'),
        (6, '6 Months'),
    )

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='weekly_order')
    shipping_address = models.ForeignKey(
        OrderShippingAddress, on_delete=models.PROTECT)
    subscription_type = models.CharField(
        max_length=10, choices=SUBSCRIPTION_TYPE_CHOICES)
    subscription_duration = models.PositiveIntegerField(
        choices=SUBSCRIPTION_DURATION_CHOICES, default=1)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField()
    end_date = models.DateField()
    next_billing_date = models.DateField(null=True, blank=True)
    next_delivery_date = models.DateField(null=True, blank=True)
    stripe_subscription_id = models.CharField(
        max_length=255, blank=True, null=True)
    stripe_payment_method_id = models.CharField(
        max_length=255, blank=True, null=True)
    stripe_setup_intent_id = models.CharField(
        max_length=255, blank=True, null=True)
    stripe_customer_id = models.CharField(
        max_length=255, blank=True, null=True)
    is_order_expire = models.BooleanField(default=False)
    is_order_active = models.BooleanField(default=False)
    is_order_pause = models.BooleanField(default=False)
    weekly_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    last_payment_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        if not self.end_date and self.start_date:
            self.end_date = self.calculate_end_date()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        return str(uuid.uuid4().int)[:12]

    def calculate_end_date(self):
        return self.start_date + relativedelta(months=self.subscription_duration)

    def is_active(self):
        return self.status == 'active' and date.today() <= self.end_date

    def get_total_weeks(self):
        """Calculate total weeks in subscription duration"""
        delta = self.end_date - self.start_date
        return delta.days // 7


class DeliveryWeek(models.Model):
    """Represents a week in the subscription with its deliveries"""
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='delivery_weeks')
    week_number = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('order', 'week_number')
        ordering = ['week_number']

    def __str__(self):
        return f"Week {self.week_number} for Order #{self.order.order_number}"


class DeliveryDay(models.Model):
    """Individual delivery days with status and items"""
    DELIVERY_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('skipped', 'Skipped'),
    )

    week = models.ForeignKey(
        DeliveryWeek, on_delete=models.CASCADE, related_name='delivery_days')
    day_name = models.CharField(max_length=20)
    delivery_date = models.DateField()
    is_cancelled = models.BooleanField(default=False)
    is_billed = models.BooleanField(default=False, blank=True,null=True)
    status = models.CharField(
        max_length=20, choices=DELIVERY_STATUS_CHOICES, default='pending')
    number_of_people = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['delivery_date']
        unique_together = ('week', 'day_name')

    def __str__(self):
        return f"{self.day_name} delivery for Week {self.week.week_number}"


class DeliveryItem(models.Model):
    """Items for each delivery day"""
    delivery_day = models.ForeignKey(
        DeliveryDay, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} for {self.delivery_day}"

    class Meta:
        app_label = 'weekly_order_manage'


class Payment(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)  # 'succeeded', 'failed'
    payment_type = models.CharField(max_length=20)  # 'weekly', 'onetime', etc.
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.status} - {self.amount} for Order {self.order.order_number}"

    class Meta:
        ordering = ['-created_at']
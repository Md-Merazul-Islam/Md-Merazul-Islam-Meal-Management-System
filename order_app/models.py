
from django.db import models
from django.contrib.auth import get_user_model
import uuid
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from products.models import Product
from areas.models import Area

User = get_user_model()


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('accepted', 'Accepted'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('paused', 'Paused'),
        ('running', 'Running'),
    )

    SUBSCRIPTION_TYPE_CHOICES = (
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )
    SUBSCRIPTION_DURATION_CHOICES = (
        ('1_month', '1 Month'),
        ('6_months', '6 Months'),
    )

    # Add this field
    subscription_duration = models.CharField(
        max_length=10,
        choices=SUBSCRIPTION_DURATION_CHOICES,
        default='1_month',
        blank=True,
        null=True
    )

    order_number = models.CharField(max_length=20, unique=True)
    subscription_type = models.CharField(
        max_length=10, choices=SUBSCRIPTION_TYPE_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()
    phone_number = models.CharField(max_length=20)
    payment_status = models.BooleanField(default=False)
    email = models.EmailField(blank=True, null=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    area = models.ForeignKey(
        Area, on_delete=models.CASCADE, blank=True, null=True)
    
    order_created_date = models.DateTimeField(auto_now_add=True)
    is_order_accepted = models.BooleanField(
        default=False, blank=True, null=True)
    stripe_subscription_id = models.CharField(
        max_length=255, blank=True, null=True)
    stripe_customer_id = models.CharField(
        max_length=255, blank=True, null=True)

    # New fields for subscription management
    is_subscription_expire = models.BooleanField(default=False, blank=True, null=True)
    is_subscription_active = models.BooleanField(default=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    card_saved = models.BooleanField(default=False)  

    is_paused = models.BooleanField(default=False, blank=True, null=True)
    pause_end_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = str(uuid.uuid4().int)[:12]
        super().save(*args, **kwargs)

    def get_next_billing_date(self):
        """Calculate next billing date based on subscription type"""
        from django.utils import timezone

        if not self.subscription_start_date:
            return None

        if self.subscription_type == 'weekly':
            # Next Monday
            days_since_monday = self.subscription_start_date.weekday()
            days_to_add = 7 - days_since_monday if days_since_monday != 0 else 7
            return self.subscription_start_date + timedelta(days=days_to_add)
        elif self.subscription_type == 'monthly':
            # Same day next month
            return self.subscription_start_date + timedelta(days=30)
        return None
    
    def calculate_subscription_end_date(self, start_date=None):
        if not start_date:
            start_date = timezone.now()

        if self.subscription_duration == '1_month':
            return start_date + relativedelta(months=1)
        elif self.subscription_duration == '6_months':
            return start_date + relativedelta(months=6)
        return None


class OrderData(models.Model):
    delivery_date = models.DateField(blank=True, null=True)
    delivery_day = models.CharField(max_length=20, blank=True, null=True)
    number_of_people = models.PositiveIntegerField(default=1)
    is_paused = models.BooleanField(default=False, blank=True, null=True)
    is_delivered = models.BooleanField(default=False, blank=True, null=True)
    is_cancelled = models.BooleanField(default=False, blank=True, null=True)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="order_data", blank=True, null=True)
    order_status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES,
        default='pending',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"OrderData for {self.delivery_date}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items')
    order_data = models.ForeignKey(
        OrderData, on_delete=models.CASCADE, related_name='order_items', blank=True, null=True)
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=255, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    revenue = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.product.name if self.product else 'No Product'} x {self.quantity}"

    def save(self, *args, **kwargs):
        if not self.product:
            raise ValueError("Cannot save OrderItem without a product.")

        if not self.revenue and self.product and self.price:
            self.revenue = (
                self.price - self.product.main_price) * self.quantity

        if self.product and not self.product_name:
            self.product_name = self.product.name

        super().save(*args, **kwargs)

class StripeCustomer(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='stripe_customer', null=True, blank=True)
    stripe_customer_id = models.CharField(
        max_length=255, unique=True, blank=True, null=True)
    default_payment_method_id = models.CharField(
        max_length=255, blank=True, null=True)
    card_last_four = models.CharField(max_length=4, blank=True, null=True)
    card_brand = models.CharField(max_length=20, blank=True, null=True)
    card_exp_month = models.IntegerField(null=True, blank=True)
    card_exp_year = models.IntegerField(null=True, blank=True)
    is_card_valid = models.BooleanField(default=True)
    stripe_subscription_id = models.CharField(
        max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"Stripe Customer: {self.user.username} - {self.stripe_customer_id}"


class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = (
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='payments')
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(
        max_length=10, choices=PAYMENT_TYPE_CHOICES)
    status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    stripe_payment_intent_id = models.CharField(
        max_length=255, blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    billing_period_start = models.DateTimeField(null=True, blank=True)
    billing_period_end = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.payment_type} - €{self.amount} "


class UserOwnSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name='own_subscription', null=True, blank=True)
    subscription = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='user_subscription', null=True)
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Subscription - {'Active' if self.is_active else 'Inactive'}"


class PauseRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='pause_request', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pause_start_date = models.DateTimeField(null=True, blank=True)
    pause_end_date = models.DateTimeField(null=True, blank=True)
    pause_reason = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pause Request for Order #{self.order.order_number} by {self.user.email}"

    def approve(self, pause_duration_days):
        self.status = 'approved'
        self.pause_start_date = self.order.order_created_date
        self.pause_end_date = self.order.order_created_date + \
            timedelta(days=pause_duration_days)
        self.save()

        # Update the order status to 'paused'
        self.order.status = 'paused'
        self.order.save()

    def reject(self):
        self.status = 'rejected'
        self.save()


class DeliverySchedule(models.Model):
    """
    Tracks all scheduled deliveries for subscriptions
    """
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='delivery_schedules')
    delivery_day = models.CharField(max_length=20)  # e.g., "Monday", "Tuesday"
    status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Pending'),
            ('preparing', 'Being Prepared'),
            ('ready', 'Ready for Delivery'),
            ('delivered', 'Delivered'),
            ('cancelled', 'Cancelled'),
        ),
        default='pending'
    )
    products = models.ManyToManyField(Product, through='DeliveryProduct')
    delivery_date = models.DateField()  # Date of the delivery
    area = models.ForeignKey(
        Area, on_delete=models.CASCADE, blank=True, null=True)
    shipping_address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DeliveryProduct(models.Model):
    """
    Products included in each delivery
    """
    delivery = models.ForeignKey(DeliverySchedule, on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True, null=True)



class DeliveryActionRequest(models.Model):
    ACTION_CHOICES = (
        ('pause', 'Pause'),
        ('cancel', 'Cancel'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES)
    delivery_dates = models.JSONField()  # List of dates to pause/cancel
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

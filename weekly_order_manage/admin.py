from django.contrib import admin
from .models import (
    OrderShippingAddress,
    StripeCustomer,
    Order,
    DeliveryWeek,
    DeliveryDay,
    DeliveryItem,
    Payment,
)


@admin.register(OrderShippingAddress)
class OrderShippingAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'email', 'postal_code', 'area')
    search_fields = ('user__username', 'phone_number', 'email', 'postal_code')
    list_filter = ('area',)


@admin.register(StripeCustomer)
class StripeCustomerAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'stripe_customer_id',
        'card_brand',
        'card_last_four',
        'card_exp_month',
        'card_exp_year',
        'is_card_valid',
        'created_at',
    )
    search_fields = ('user__username', 'stripe_customer_id', 'card_last_four')
    list_filter = ('card_brand', 'is_card_valid', 'created_at')


class DeliveryItemInline(admin.TabularInline):
    model = DeliveryItem
    extra = 1
    readonly_fields = ('created_at',)


@admin.register(DeliveryDay)
class DeliveryDayAdmin(admin.ModelAdmin):
    list_display = ('week', 'day_name', 'delivery_date',
                    'status', 'is_cancelled', 'number_of_people')
    list_filter = ('status', 'is_cancelled', 'delivery_date')
    search_fields = ('day_name', 'week__order__order_number')
    inlines = [DeliveryItemInline]


@admin.register(DeliveryWeek)
class DeliveryWeekAdmin(admin.ModelAdmin):
    list_display = ('order', 'week_number', 'created_at')
    search_fields = ('order__order_number',)
    ordering = ('order', 'week_number')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'user',
        'status',
        'subscription_type',
        'subscription_duration',
        'start_date',
        'end_date',
        'next_billing_date',
        'total_amount',
        'is_order_active',
        'created_at',
    )
    list_filter = ('status', 'subscription_type',
                   'subscription_duration', 'is_order_active', 'created_at')
    search_fields = ('order_number', 'user__username',
                     'stripe_subscription_id')
    date_hierarchy = 'created_at'
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    autocomplete_fields = ('user', 'shipping_address')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'amount',
        'status',
        'payment_type',
        'billing_period_start',
        'billing_period_end',
        'created_at',
    )
    list_filter = ('status', 'payment_type', 'created_at')
    search_fields = ('order__order_number', 'stripe_payment_intent_id')
    date_hierarchy = 'created_at'


# Register models without custom admin if desired:
# admin.site.register(DeliveryItem) # Already handled via inline in DeliveryDayAdmin

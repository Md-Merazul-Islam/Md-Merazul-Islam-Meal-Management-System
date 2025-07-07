from .models import (
    StripeCustomer,
    Payment,
    UserOwnSubscription,
    PauseRequest,
    DeliverySchedule,
    DeliveryProduct
)
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Order, OrderData, OrderItem, Payment, PauseRequest
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError


class OrderItemInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                product = form.cleaned_data.get('product')
                if not product:
                    raise ValidationError(
                        "All Order Items must have a product selected.")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1  # or 0
    fields = ['product', 'quantity', 'price', 'revenue']
    formset = OrderItemInlineFormSet


class OrderDataInline(admin.TabularInline):
    model = OrderData
    extra = 1
    fields = ['delivery_day', 'number_of_people', 'order_status',
              'is_paused', 'is_delivered', 'is_cancelled']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'id', 'user', 'status', 'subscription_type',
        'subscription_duration', 'is_subscription_active',
        'is_subscription_expire', 'subscription_start_date',
        'subscription_end_date', 'next_billing_date',
        'payment_status', 'card_saved'
    )

    list_filter = (
        'status', 'subscription_type', 'subscription_duration',
        'is_subscription_active', 'is_subscription_expire', 'card_saved'
    )

    search_fields = (
        'order_number', 'user__username', 'user__email', 'phone_number', 'email'
    )

    readonly_fields = (
        'order_number', 'order_created_date', 'subscription_end_date',
        'next_billing_date'
    )

    fieldsets = (
        ('Order Details', {
            'fields': ('order_number', 'user', 'status', 'total_amount', 'shipping_address',
                       'phone_number', 'email', 'postal_code', 'area', 'order_created_date')
        }),
        ('Subscription Info', {
            'fields': ('subscription_type', 'subscription_duration',
                       'subscription_start_date', 'subscription_end_date',
                       'next_billing_date', 'is_subscription_active', 'is_subscription_expire',
                       'is_paused', 'pause_end_date')
        }),
        ('Payment Info', {
            'fields': ('payment_status', 'payment_date', 'card_saved',
                       'stripe_subscription_id', 'stripe_customer_id')
        }),
    )

    def has_add_permission(self, request):
        return True

@admin.register(OrderData)
class OrderDataAdmin(admin.ModelAdmin):
    list_display = ['delivery_day', 'order', 'order_status',
                    'is_paused', 'is_delivered', 'is_cancelled']
    search_fields = ['order__order_number', 'order__user__email']
    list_filter = ['order_status', 'is_paused', 'is_delivered', 'is_cancelled']
    inlines = [OrderItemInline]



@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price', 'revenue']
    search_fields = ['order__order_number', 'product__name']
    list_filter = ['order__status', 'product__name']
    raw_id_fields = ['order', 'product']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'status', 'payment_date']
    list_filter = ['status', 'payment_date']
    raw_id_fields = ['order']



@admin.register(PauseRequest)
class PauseRequestAdmin(admin.ModelAdmin):
    list_display = ['order', 'user', 'pause_start_date',
                    'pause_end_date', 'pause_reason', 'status', 'requested_at']
    search_fields = ['order__order_number', 'user__email', 'pause_reason']
    list_filter = ['status']
    raw_id_fields = ['order', 'user']


@admin.register(StripeCustomer)
class StripeCustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'stripe_customer_id', 'card_brand',
                    'card_last_four', 'is_card_valid', 'created_at')
    search_fields = ('user__username', 'stripe_customer_id', 'card_last_four')
    list_filter = ('is_card_valid', 'card_brand')


@admin.register(UserOwnSubscription)
class UserOwnSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription', 'total_amount',
                    'is_active', 'start_date', 'end_date')
    search_fields = ('user__username',)
    list_filter = ('is_active',)


class DeliveryProductInline(admin.TabularInline):
    model = DeliveryProduct
    extra = 1


@admin.register(DeliverySchedule)
class DeliveryScheduleAdmin(admin.ModelAdmin):
    list_display = ('order', 'delivery_day', 'delivery_date', 'status', 'area')
    list_filter = ('status', 'delivery_day', 'delivery_date')
    search_fields = ('order__order_number',)
    inlines = [DeliveryProductInline]
    date_hierarchy = 'delivery_date'
    ordering = ['delivery_date']


@admin.register(DeliveryProduct)
class DeliveryProductAdmin(admin.ModelAdmin):
    list_display = ('delivery', 'product', 'quantity')
    search_fields = ('delivery__order__order_number', 'product__name')

from rest_framework import serializers
from .models import (
    OrderShippingAddress, StripeCustomer, Order,
    DeliveryWeek, DeliveryDay, DeliveryItem
)
from products.serializers import ProductSerializer, Product
from areas.serializers import AreaSerializer, Area
from dateutil.relativedelta import relativedelta


class OrderShippingAddressSerializer(serializers.ModelSerializer):
    area = AreaSerializer(read_only=True)
    area_id = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(),
        source='area',
        write_only=True
    )

    class Meta:
        model = OrderShippingAddress
        fields = [
            'id', 'user', 'shipping_address', 'phone_number', 'email',
            'postal_code', 'area', 'area_id',
        ]
        read_only_fields = ['user', ]


class StripeCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StripeCustomer
        fields = [
            'id', 'user', 'stripe_customer_id', 'default_payment_method_id',
            'card_last_four', 'card_brand', 'card_exp_month', 'card_exp_year',
            'is_card_valid', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']


class DeliveryItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )

    class Meta:
        model = DeliveryItem
        fields = ['id', 'product', 'product_id', 'quantity', 'created_at']
        read_only_fields = ['created_at']


class DeliveryDaySerializer(serializers.ModelSerializer):
    order_items = DeliveryItemSerializer(many=True, read_only=True)
    item_ids = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of product IDs and quantities for this delivery day"
    )

    class Meta:
        model = DeliveryDay
        fields = [
            'id', 'week', 'day_name', 'delivery_date', 'is_cancelled',
            'status', 'number_of_people', 'order_items', 'item_ids',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class DeliveryWeekSerializer(serializers.ModelSerializer):
    delivery_days = DeliveryDaySerializer(many=True, read_only=True)

    class Meta:
        model = DeliveryWeek
        fields = ['id', 'order', 'week_number', 'delivery_days', 'created_at']
        read_only_fields = ['created_at']


class OrderSerializer(serializers.ModelSerializer):
    shipping_address = OrderShippingAddressSerializer(read_only=True)
    shipping_address_id = serializers.PrimaryKeyRelatedField(
        queryset=OrderShippingAddress.objects.all(),
        source='shipping_address',
        write_only=True
    )
    delivery_weeks = DeliveryWeekSerializer(many=True, read_only=True)
    selected_days = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of day names (e.g., ['Monday', 'Wednesday']) for weekly or dates (e.g., ['5', '15']) for monthly"
    )
    delivery_items = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of delivery day configurations with products"
    )

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'shipping_address', 'shipping_address_id',
            'subscription_type', 'subscription_duration', 'status', 'start_date',
            'end_date', 'next_billing_date', 'next_delivery_date',
            'stripe_subscription_id', 'stripe_payment_method_id', 'stripe_setup_intent_id',
            'weekly_amount', 'total_amount', 'delivery_weeks', 'selected_days',
            'delivery_items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user', 'order_number', 'end_date', 'next_billing_date',
            'next_delivery_date', 'stripe_subscription_id', 'stripe_payment_method_id',
            'stripe_setup_intent_id', 'total_amount', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        selected_days = validated_data.pop('selected_days', [])
        delivery_items = validated_data.pop('delivery_items', [])
        request = self.context.get('request')

        # Calculate total amount (simplified - should be based on products and duration)
        total_amount = 100 * \
            validated_data['subscription_duration']  # Placeholder

        order = Order.objects.create(
            user=request.user,
            total_amount=total_amount,
            weekly_amount=total_amount /
            (validated_data['subscription_duration'] * 4),  # Approx weeks
            **validated_data
        )

        # Generate all delivery weeks and days for the entire duration
        self.generate_delivery_schedule(order, selected_days, delivery_items)

        return order

    def generate_delivery_schedule(self, order, selected_days, delivery_items):
        """Generate complete delivery schedule for the entire subscription duration"""
        from datetime import datetime, timedelta

        current_date = order.start_date
        end_date = order.end_date
        week_number = 1

        if order.subscription_type == 'weekly':
            # Weekly delivery - generate all weeks with selected days
            while current_date <= end_date:
                week = DeliveryWeek.objects.create(
                    order=order,
                    week_number=week_number
                )

                # Create delivery days for each selected day in this week
                for day_name in selected_days:
                    # Find next occurrence of this day
                    days_ahead = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                                  'Friday', 'Saturday', 'Sunday'].index(day_name) - current_date.weekday()
                    if days_ahead < 0:
                        days_ahead += 7
                    delivery_date = current_date + timedelta(days=days_ahead)

                    if delivery_date <= end_date:
                        # Find items for this day from delivery_items
                        day_items = next(
                            (item for item in delivery_items if item['day_name'] == day_name),
                            {'number_of_people': 1, 'products': []}
                        )

                        delivery_day = DeliveryDay.objects.create(
                            week=week,
                            day_name=day_name,
                            delivery_date=delivery_date,
                            number_of_people=day_items.get(
                                'number_of_people', 1)
                        )

                        # Add products to this delivery day
                        for product_item in day_items.get('products', []):
                            DeliveryItem.objects.create(
                                delivery_day=delivery_day,
                                product_id=product_item['product_id'],
                                quantity=product_item['quantity']
                            )

                # Move to next week
                current_date += timedelta(days=7)
                week_number += 1
        else:
            # Monthly delivery - generate all months with selected dates
            while current_date <= end_date:
                week = DeliveryWeek.objects.create(
                    order=order,
                    week_number=week_number
                )

                for day_num in selected_days:
                    try:
                        day_num = int(day_num)
                        delivery_date = current_date.replace(day=day_num)

                        if delivery_date >= current_date and delivery_date <= end_date:
                            day_name = delivery_date.strftime('%A')

                            # Find items for this date from delivery_items
                            day_items = next(
                                (item for item in delivery_items if item['day_name'] == str(
                                    day_num)),
                                {'number_of_people': 1, 'products': []}
                            )

                            delivery_day = DeliveryDay.objects.create(
                                week=week,
                                day_name=day_name,
                                delivery_date=delivery_date,
                                number_of_people=day_items.get(
                                    'number_of_people', 1)
                            )

                            # Add products to this delivery day
                            for product_item in day_items.get('products', []):
                                DeliveryItem.objects.create(
                                    delivery_day=delivery_day,
                                    product_id=product_item['product_id'],
                                    quantity=product_item['quantity']
                                )
                    except ValueError:
                        continue  # Skip invalid day numbers

                # Move to next month
                current_date = current_date.replace(
                    day=1) + relativedelta(months=1)
                week_number += 1

        # Set first delivery date
        first_delivery = DeliveryDay.objects.filter(
            week__order=order
        ).order_by('delivery_date').first()

        if first_delivery:
            order.next_delivery_date = first_delivery.delivery_date
            order.save()


class OrderListSerializer(serializers.ModelSerializer):
    user_address = OrderShippingAddressSerializer(
        source='shipping_address', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'status', 'start_date', 'end_date',
                  'is_order_active', 'is_order_pause', 'total_amount', 'created_at', 'user_address']


class DeliverListSerializer(serializers.ModelSerializer):
    user_address = serializers.SerializerMethodField(source='week.order.shipping_address', read_only=True)
    order_items = DeliveryItemSerializer(many=True, read_only=True)
    order_number = serializers.CharField(source='week.order.order_number', read_only=True)
    item_ids = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of product IDs and quantities for this delivery day"
    )

    class Meta:
        model = DeliveryDay
        fields = [
            'id','order_number', 'week', 'day_name', 'delivery_date', 'is_cancelled',
            'status', 'number_of_people', 'item_ids',
            'created_at', 'updated_at', 'user_address', 'order_items',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_user_address(self, obj):
        # Make sure related_name or field exists like obj.week.order.shipping_address
        try:
            shipping_address = obj.week.order.shipping_address
            return OrderShippingAddressSerializer(shipping_address).data
        except AttributeError:
            return None

class CancelDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryDay
        fields = ['id', 'is_cancelled']

class OrderPauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'is_order_pause']
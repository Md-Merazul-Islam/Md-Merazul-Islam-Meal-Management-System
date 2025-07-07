
from .models import DeliveryActionRequest, Order
from .models import DeliverySchedule, DeliveryProduct
from rest_framework import serializers
from .models import Order, OrderItem, OrderData, PauseRequest
from products.models import Product
from areas.models import Area
from areas.serializers import AreaSerializerDetail
from django.contrib.auth import get_user_model
from datetime import date, timedelta
import calendar

User = get_user_model()


class ProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'image']


class OrderItemCreateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class OrderDataCreateSerializer(serializers.Serializer):
    delivery_date = serializers.DateField(required=False, allow_null=True)
    delivery_day = serializers.CharField(required=False, allow_null=True)
    number_of_people = serializers.IntegerField(min_value=1)
    order_items = OrderItemCreateSerializer(many=True)


class OrderItemSerializer(serializers.ModelSerializer):
    product_details = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_details',
                  'quantity', 'price', 'revenue']
        read_only_fields = ['id', 'revenue', 'price']

    def get_product_details(self, obj):
        image_url = None
        if obj.product.image:
            if hasattr(obj.product.image, 'url'):
                image_url = obj.product.image.url
            else:
                image_url = obj.product.image

        return {
            "image": image_url,
            "name": obj.product.name,
            "price": obj.product.price,
            "revenue": obj.product.revenue,
        }



class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class OrderCreateSerializer(serializers.Serializer):
    subscription_type = serializers.ChoiceField(
        choices=Order.SUBSCRIPTION_TYPE_CHOICES)
    shipping_address = serializers.CharField()
    phone_number = serializers.CharField()
    postal_code = serializers.CharField(required=False, allow_null=True)
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), required=False, allow_null=True)
    email = serializers.EmailField(required=False, allow_null=True)
    total_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True)

    order_data = OrderDataCreateSerializer(many=True)

    def create(self, validated_data, **extra_fields):
        user = self.context['request'].user
        order_data_list = validated_data.pop('order_data')

        
        total_amount = extra_fields.pop('total_amount', None)
        if total_amount is None:
            total_amount = 0
            for order_data in order_data_list:
                for item in order_data['order_items']:
                    product = item['product']
                    quantity = item['quantity']
                    total_amount += product.price * quantity

        
        validated_data.pop('total_amount', None)

        
        order_create_data = {
            'user': user,
            'total_amount': total_amount,
            **validated_data,
            **extra_fields,
        }

        order = Order.objects.create(**order_create_data)

        
        for order_data_dict in order_data_list:
            order_items_data = order_data_dict.pop('order_items')
            order_data = OrderData.objects.create(
                order=order, **order_data_dict)

            for item_data in order_items_data:
                product = item_data['product']
                quantity = item_data['quantity']
                price = product.price

                revenue = 0
                if hasattr(product, 'main_price'):
                    revenue = (price - product.main_price) * quantity

                OrderItem.objects.create(
                    order=order,
                    order_data=order_data,
                    product=product,
                    quantity=quantity,
                    price=price,
                    revenue=revenue
                )

        return order


class OrderItemSerializer_TTTTT(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'quantity', 'price', 'revenue']


class OrderSerializer_TTTT(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            'order_number',
            'status',
            'is_paused',
            'pause_end_date',
            'subscription_type',
            'is_subscription_active',
            'subscription_start_date',
            'subscription_end_date',
            'next_billing_date',
            
        ]


class OrderDataSerializer(serializers.ModelSerializer):
    
    order_items = OrderItemSerializer_TTTTT(many=True)

    username = serializers.CharField(
        source='order.user.get_full_name', read_only=True)
    shipping_address = serializers.CharField(
        source='order.shipping_address', read_only=True)
    email = serializers.EmailField(source='order.email', read_only=True)
    phone_number = serializers.CharField(
        source='order.phone_number', read_only=True)
    area = serializers.CharField(source='order.area.name', read_only=True)
    postal_code = serializers.CharField(
        source='order.postal_code', read_only=True)
    order_status = serializers.CharField(read_only=True)

    converted_delivery_date = serializers.SerializerMethodField()
    order = OrderSerializer_TTTT(read_only=True)

    class Meta:
        model = OrderData
        fields = [
            'id',
            'delivery_date',
            'delivery_day',
            'converted_delivery_date',
            'number_of_people',
            'is_paused',
            'is_delivered',
            'is_cancelled',
            'order_status',
            'username',
            'shipping_address',
            'email',
            'phone_number',
            'postal_code',
            'area',
            'order',
            'order_items',
        ]

    def get_converted_delivery_date(self, obj):
        pass


class OrderDetailSerializer(serializers.ModelSerializer):
    user_details = UserBasicSerializer(source='user', read_only=True)
    area_details = AreaSerializerDetail(source='area', read_only=True)
    order_data_details = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'subscription_type', 'status', 'user',
                  'user_details', 'total_amount', 'shipping_address', 'phone_number', 'is_subscription_active', 'subscription_start_date', 'subscription_end_date',
                  'payment_status', 'is_order_accepted', 'email', 'payment_date',
                  'postal_code', 'area', 'area_details', 'order_created_date',
                  'order_data_details',]
        read_only_fields = ['id', 'order_number', 'order_created_date']

    def get_order_data_details(self, obj):
        
        order_data_instances = OrderData.objects.filter(order=obj)
        return OrderDataSerializer(order_data_instances, many=True).data


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status', 'payment_status', 'payment_date']


class OrderAcceptanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['is_order_accepted']


class PauseRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PauseRequest
        fields = ['user', 'order', 'status', 'pause_reason',
                  'pause_start_date', 'pause_end_date']

    def validate(self, data):
        
        if data.get('pause_end_date') <= data.get('pause_start_date'):
            raise serializers.ValidationError(
                "End date must be after start date")
        return data


class OrderAcceptanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['is_order_accepted']


class OrderDataForAdminSerializer(serializers.ModelSerializer):
    shipping_address = serializers.CharField(source='order.shipping_address')
    postal_code = serializers.CharField(source='order.postal_code')
    user_details = UserBasicSerializer(source='order.user', read_only=True)
    phone_number = serializers.CharField(source='order.phone_number')
    email = serializers.EmailField(source='order.email')
    items = OrderItemSerializer(
        many=True, source='order_items', read_only=True)
    area = serializers.CharField(source='order.area.name', read_only=True)

    class Meta:
        model = OrderData
        fields = [
            'id',
            'delivery_date',
            "delivery_day",
            'user_details',
            'number_of_people',
            'is_delivered',
            'is_cancelled',
            'order_status',
            'items',
            'shipping_address',
            'postal_code',
            'phone_number',
            'email',
            'area',
        ]


class AreaRevenueSerializer(serializers.ModelSerializer):
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Area
        fields = ['id', 'name', 'total_revenue']


class OrderItemInputSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    quantity = serializers.IntegerField()


class DeliveryProductSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(
        source='product.price', read_only=True, max_digits=10, decimal_places=2)

    class Meta:
        model = DeliveryProduct
        fields = ['id', 'product_id', 'product_name',
                  'product_price', 'quantity', 'notes']


class DeliveryScheduleSerializer(serializers.ModelSerializer):
    products = DeliveryProductSerializer(
        many=True, read_only=True, source='deliveryproduct_set')
    area_name = serializers.CharField(source='area.name', read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()

    class Meta:
        model = DeliverySchedule
        fields = [
            'id', 'order', 'delivery_day', 'delivery_date', 'status',
            'area', 'area_name', 'shipping_address', 'phone_number',
            'postal_code', 'email', 'products', 'customer_name',
            'customer_phone', 'customer_email', 'created_at', 'updated_at'
        ]

    def get_customer_name(self, obj):
        if obj.order and obj.order.user:
            return obj.order.user.get_full_name()
        return obj.email or "No name provided"

    def get_customer_phone(self, obj):
        return obj.phone_number

    def get_customer_email(self, obj):
        return obj.email


class DeliveryActionRequestSerializer(serializers.ModelSerializer):
    user_info = UserBasicSerializer(source='user', read_only=True)
    order_information = OrderSerializer_TTTT(read_only=True, source='order')

    class Meta:
        model = DeliveryActionRequest
        fields = ['id', 'order', 'action_type', 'delivery_dates', 'reason',
                  'status', 'created_at', 'user', 'user_info', 'order_information']


class SubscriptionStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'is_subscription_active',
                  'subscription_start_date', 'subscription_end_date']

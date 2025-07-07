from .models import CancelDelivery
from rest_framework import serializers
from auths.serializers import UserSerializer
from weekly_order_manage.serializers import DeliveryDaySerializer


class CancelDeliverySerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='user', read_only=True)
    delivery_day_details = DeliveryDaySerializer(
        source='delivery_day', read_only=True)

    class Meta:
        model = CancelDelivery
        fields = [
            'id',
            'user',
            'reason',
            'request_status',
            'created_at',
            'updated_at',
            'delivery_day',
            'user_info',
            'delivery_day_details'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']


from rest_framework import serializers
from .models import Box, FreeBoxRequest
from areas.models import Area, PostalCode
from products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name']  # Only includes id and name

class BoxSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True, source='items')
    
    class Meta:
        model = Box
        fields = ['id', 'name', 'products'] 

class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']


class FreeBoxRequestSerializer(serializers.ModelSerializer):
    area_name = AreaSerializer(read_only=True)
    box_info = BoxSerializer(read_only=True, source='box')

    class Meta:
        model = FreeBoxRequest
        fields = [
            'id', 'number_of_people', 'date_of_delivery', 'box', 'name',
            'phone_number', 'postal_code', 'address', 'area_name', 'email', 'message', 'delivery_status', 'box_info', 'create_at'
        ]

    def create(self, validated_data):
        postal_code = validated_data.get('postal_code')
        try:
            postal_code_instance = PostalCode.objects.get(code=postal_code)
            validated_data['area_name'] = postal_code_instance.area
        except PostalCode.DoesNotExist:
            validated_data['area_name'] = None
        return super().create(validated_data)

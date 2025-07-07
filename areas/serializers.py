from .models import DeliveryManArea, Review,Area, PostalCode
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from auths.serializers import UserSerializer
from utils.success_failer import success_response,failure_response
User = get_user_model()

class AreaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Area
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']


class PostalCodeSerializer(serializers.ModelSerializer):
    area_info = AreaSerializer(read_only=True, source='area')

    class Meta:
        model = PostalCode
        fields = ['id', 'code', 'area', 'area_info']


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'delivery_man', 'user',
                  'rating', 'review_text', 'created_at']


class DeliveryManAreaSerializer(serializers.ModelSerializer):
    reviews = ReviewSerializer(many=True, read_only=True)
    delivery_man_info= UserSerializer(read_only=True, source='delivery_man')
    area_info = AreaSerializer(read_only=True, source='area')
    class Meta:
        model = DeliveryManArea
        fields = ['id', 'delivery_man', 'area', 'create_at', 'average_rating', 'reviews','delivery_man_info','area_info']

    def create(self, validated_data):
       
        delivery_man_id = validated_data.get('delivery_man')
        if isinstance(delivery_man_id, int): 
            validated_data['delivery_man'] = User.objects.get(id=delivery_man_id)
        
       
        area_id = validated_data.get('area')
        if isinstance(area_id, int): 
            validated_data['area'] = Area.objects.get(id=area_id)

        existing_area = DeliveryManArea.objects.filter(delivery_man=validated_data['delivery_man'], area=validated_data['area']).first()
        if existing_area:
            raise ValidationError({
                "detail": "This delivery man is already assigned to this area.",
                "error_code": "DUPLICATE_ASSIGNMENT",
                "status": status.HTTP_400_BAD_REQUEST,
                "success": False,
                "additional_info": {
                    "delivery_man_id": validated_data['delivery_man'].id,
                    "area_id": validated_data['area'].id
                }
            })
        return super().create(validated_data)
    

class PostalCodeSerializerT(serializers.ModelSerializer):
    class Meta:
        model = PostalCode
        fields = ['id', 'code']
    
class AreaSerializer(serializers.ModelSerializer):
    # Adding detailed postal codes info
    postal_codes = PostalCodeSerializerT(many=True, read_only=True)

    class Meta:
        model = Area
        fields = ['id', 'name', 'slug', 'postal_codes']
        
class AreaSerializerDetail(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ['id', 'name', 'slug']
        
        
    
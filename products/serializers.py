from rest_framework import serializers
from .models import Product, Category
from utils.upload_utils import upload_file_to_digital_ocean,delete_file_from_s3

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']

class ProductSerializer(serializers.ModelSerializer):
    image_tmp = serializers.FileField(write_only=True, required=False)
    
    class Meta:
        model = Product
        fields = ['id', 'name','main_price', 'price', 'revenue','description', 'image', 'category', 'image_tmp']
        read_only_fields = ['image','revenue']
    
    def create(self, validated_data):
        """
        Handle product creation, uploading the image to DigitalOcean and saving the product.
        """
        image_tmp = validated_data.pop('image_tmp', None)
        if not image_tmp:
            raise serializers.ValidationError({"image_tmp": "An image file must be provided."})

        uploaded_image = upload_file_to_digital_ocean(image_tmp)
        validated_data['image'] = uploaded_image

        return Product.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Handle product updates. Image upload is optional, only update image if provided.
        """
        image_tmp = validated_data.pop('image_tmp', None)
        
        if image_tmp:
            if instance.image:
                delete_file_from_s3(instance.image)
            uploaded_image = upload_file_to_digital_ocean(image_tmp)
            validated_data['image'] = uploaded_image

        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

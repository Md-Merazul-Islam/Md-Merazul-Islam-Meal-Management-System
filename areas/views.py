from rest_framework import viewsets
from .models import Area, PostalCode,Review,DeliveryManArea
from .serializers import AreaSerializer, PostalCodeSerializer,ReviewSerializer,DeliveryManAreaSerializer
from rest_framework.filters import SearchFilter
from utils.crud import DynamicModelViewSet
from utils.pagination import CustomPagination
from utils.IsAdminuser import IsAdminOrHasRoleAdmin
class AreaViewSet(DynamicModelViewSet):
    queryset = Area.objects.all().order_by('id')
    serializer_class = AreaSerializer
    pagination_class = CustomPagination
    # permission_classes = [IsAdminOrHasRoleAdmin]

    def __init__(self, *args, **kwargs):
        kwargs['model'] = Area
        kwargs['serializer_class'] = AreaSerializer
        kwargs['item_name'] = 'Ares'
        super().__init__(*args, **kwargs)

class PostalCodeViewSet(DynamicModelViewSet):
    queryset = PostalCode.objects.all()
    serializer_class = PostalCodeSerializer
    filter_backends = [SearchFilter]
    search_fields = ['code']
    queryset = Area.objects.all()
    # permission_classes = [IsAdminOrHasRoleAdmin]

    def __init__(self, *args, **kwargs):
        kwargs['model'] = PostalCode
        kwargs['serializer_class'] = PostalCodeSerializer
        kwargs['item_name'] = 'Postal Code'
        super().__init__(*args, **kwargs)

class ReviewViewSet(DynamicModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    pagination_class= CustomPagination
    
      
    def __init__(self, *args, **kwargs):
        kwargs['model'] = Review
        kwargs['serializer_class'] = ReviewSerializer
        kwargs['item_name'] = 'Review'
        super().__init__(*args, **kwargs)

class DeliveryManAreaViewSet(DynamicModelViewSet):
    queryset = DeliveryManArea.objects.all()
    serializer_class = DeliveryManAreaSerializer
    pagination_class= CustomPagination
    
    
      
    def __init__(self, *args, **kwargs):
        kwargs['model'] = DeliveryManArea
        kwargs['serializer_class'] = DeliveryManAreaSerializer
        kwargs['item_name'] = 'Delivery men area'
        super().__init__(*args, **kwargs)
    
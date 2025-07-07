from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AreaViewSet, PostalCodeViewSet,DeliveryManAreaViewSet,ReviewViewSet

router = DefaultRouter()
router.register(r'name', AreaViewSet, basename='area-name')
router.register(r'postal-codes', PostalCodeViewSet, basename='postal_code')
router.register(r'delivery-man-areas', DeliveryManAreaViewSet)
router.register(r'reviews', ReviewViewSet)


urlpatterns = [
    path('', include(router.urls)),
]

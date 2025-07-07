
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet, DeliveryDayViewSet, SetupCardForSubscriptionView, ConfirmCardAndCreateSubscriptionView, OrderListAPIView, OrderDetailAPIView, DeliveryDayListAPIView, AllDeliveryDayAPIView, SingleDeliveryDayAPIView, CancelDeliveryDayAPIView,OrderPauseAPIView)

router = DefaultRouter()

router.register(r'orders', OrderViewSet, basename='order')
router.register(r'delivery-days', DeliveryDayViewSet, basename='delivery-day')

urlpatterns = [
    path('', include(router.urls)),
    path('setup-card/', SetupCardForSubscriptionView.as_view(), name='setup_card'),
    path('confirm-subscription/', ConfirmCardAndCreateSubscriptionView.as_view(),name='confirm_subscription'),

    # my order
    path('all-orders/', OrderListAPIView.as_view(), name='order-list'),
    path('all-orders/<int:pk>/', OrderDetailAPIView.as_view(), name='order-detail'),

    # admin panel
    path('admin/all/delivery-days/', DeliveryDayListAPIView.as_view(), name='delivery-day-list'),
    path('cancel/delivery-days/<int:pk>/', CancelDeliveryDayAPIView.as_view(), name='delivery-day-detail'),

    path('all/delivery-days/<int:pk>/', SingleDeliveryDayAPIView.as_view(), name='delivery-day-detail'),

    path('deliveryman/all/delivery-days/', AllDeliveryDayAPIView.as_view(),name='delivery-day-list'),
    
    
    #order pause 
    path('pause/<int:pk>/', OrderPauseAPIView.as_view(), name='order-pause'),
]

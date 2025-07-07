from .views import CancelDeliveryDetailView,  CancelDeliveryView,ApproveCancelRequest,RejectCancelRequest,ReadOnlyCancelDeliveryViewSet,CancelDeliveryView

from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'cancel-delivery-list', ReadOnlyCancelDeliveryViewSet, basename='product-read')

urlpatterns = [
  path('', include(router.urls)),
  #create cancel delivery
  path('cancel-delivery/', CancelDeliveryView.as_view(), name='cancel-delivery-create'),
  
  path('cancel-delivery/<int:pk>/', CancelDeliveryDetailView.as_view(), name='cancel-delivery-detail'),
  
  
  #cancel & approve request
  path('cancel-delivery/<int:pk>/approve/', ApproveCancelRequest.as_view(), name='cancel-delivery-approve'),
  path('cancel-delivery/<int:pk>/reject/', RejectCancelRequest.as_view(), name='cancel-delivery-reject'),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BoxViewSet,FreeBoxRequestViewSet,FreeBoxRequestCreateAPIView

# Create a router and register the BoxViewSet
router = DefaultRouter()
router.register(r'trail/boxes', BoxViewSet)
router.register(r'free-box-requests', FreeBoxRequestViewSet)
urlpatterns = [
    path('', include(router.urls)),  
    path('create/new-request/', FreeBoxRequestCreateAPIView.as_view(), name='free-box-request-create')
]

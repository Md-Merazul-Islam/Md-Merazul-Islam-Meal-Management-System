# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet,ReadOnlyCategoryViewSet, ReadOnlyProductViewSet

router = DefaultRouter()
#admin can only access
router.register(r'categories/add', CategoryViewSet, basename='category')
router.register(r'new-add', ProductViewSet, basename='product')

# Register the Read-Only viewsets for categories and products
router.register(r'categories/list', ReadOnlyCategoryViewSet, basename='category-read')
router.register(r'list', ReadOnlyProductViewSet, basename='product-read')


urlpatterns = [
    path('', include(router.urls)),
]

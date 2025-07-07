
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from .permissions import IsAdminOrHasRoleAdmin  
from rest_framework.pagination import PageNumberPagination
from utils.upload_utils import  delete_file_from_s3
def success_response(message, data, status_code=status.HTTP_200_OK):
    return Response({
        "success": True,
        "statusCode": status_code,
        "message": message,
        "data": data
    }, status=status_code)


def failure_response(message, error, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({
        "success": False,
        "statusCode": status_code,
        "message": message,
        "error": error
    }, status=status_code)



class CustomPagination(PageNumberPagination):
    page_size = 10 
    page_size_query_param = 'page_size' 
    max_page_size = 100 

class ReadOnlyCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class=CustomPagination
    permission_classes = [AllowAny] 

    def list(self, request, *args, **kwargs):
        categories = self.get_queryset()
        serializer = self.get_serializer(categories, many=True)
        return Response({
            "success": True,
            "message": "Category list retrieved successfully",
            "data": serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category)
        return Response({
            "success": True,
            "message": "Category details retrieved successfully",
            "data": serializer.data
        })


class ReadOnlyProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]  
    
    def get_queryset(self):
        category_id = self.request.query_params.get('category', None)
        if category_id:
            return Product.objects.filter(category_id=category_id).order_by('id')
        return Product.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        products = self.get_queryset()
        serializer = self.get_serializer(products, many=True)
        
       
        data = {
            "count": products.count(),
            "next": None, 
            "previous": None, 
            "results": serializer.data
        }
        
        return success_response("Product list retrieved successfully", data)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    permission_classes = [IsAdminOrHasRoleAdmin] 

    def list(self, request, *args, **kwargs):
        categories = self.get_queryset()
        serializer = self.get_serializer(categories, many=True)
        return success_response("Category list retrieved successfully", serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            return success_response("Category created successfully", CategorySerializer(category).data, status.HTTP_201_CREATED)
        return failure_response("Category creation failed", serializer.errors)

    def retrieve(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category)
        return success_response("Category details retrieved successfully", serializer.data)

    def update(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category, data=request.data, partial=False)
        if serializer.is_valid():
            category = serializer.save()
            return success_response("Category updated successfully", CategorySerializer(category).data)
        return failure_response("Category update failed", serializer.errors)

    def partial_update(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            category = serializer.save()
            return success_response("Category partially updated successfully", CategorySerializer(category).data)
        return failure_response("Category partial update failed", serializer.errors)

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        category.delete()
        return success_response("Category deleted successfully", {}, status.HTTP_204_NO_CONTENT)


    

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdminOrHasRoleAdmin]


    def get_queryset(self):
        category_id = self.request.query_params.get('category', None)
        if category_id:
            return Product.objects.filter(category_id=category_id).order_by('id')
        return Product.objects.all().order_by('id')

   
    def list(self, request, *args, **kwargs):
        products = self.get_queryset()
        page = self.paginate_queryset(products) 
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(products, many=True)
        return success_response("Product list retrieved successfully", serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            return success_response("Product created successfully", ProductSerializer(product).data, status.HTTP_201_CREATED)
        return failure_response("Product creation failed", serializer.errors)

    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(product)
        return success_response("Product details retrieved successfully", serializer.data)

    def update(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(product, data=request.data, partial=False)
        if serializer.is_valid():
            product = serializer.save()
            return success_response("Product updated successfully", ProductSerializer(product).data)
        return failure_response("Product update failed", serializer.errors)

    def partial_update(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            product = serializer.save()
            return success_response("Product partially updated successfully", ProductSerializer(product).data)
        return failure_response("Product partial update failed", serializer.errors)

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if product.image:
            delete_file_from_s3(product.image)
        product = self.get_object()
        product.delete()
        return success_response("Product deleted successfully", {}, status.HTTP_200_OK)

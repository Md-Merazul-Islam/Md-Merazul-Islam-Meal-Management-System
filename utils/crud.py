from rest_framework import viewsets, status
from rest_framework.response import Response
from .success_failer import success_response, failure_response  

class DynamicModelViewSet(viewsets.ModelViewSet):
    """
    A dynamic viewset to handle CRUD operations for any model and serializer.
    It requires the model, serializer, and item name to be passed when initializing.
    """
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', None)
        self.serializer_class = kwargs.pop('serializer_class', None)
        self.item_name = kwargs.pop('item_name', None)
        super().__init__(*args, **kwargs)
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.model.objects.all().order_by('-id')
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)
            return success_response(f"All {self.item_name}s fetched successfully.", serializer.data, status.HTTP_200_OK)
        except Exception as e:
            return failure_response(f"Failed to fetch {self.item_name}s.", {"detail": str(e)})

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(f"{self.item_name} created successfully.", serializer.data, status.HTTP_201_CREATED)
        else:
            return failure_response("Invalid data.", serializer.errors, status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            item = self.model.objects.get(pk=kwargs.get('pk'))
            serializer = self.serializer_class(item)
            return success_response(f"{self.item_name} Details", serializer.data, status.HTTP_200_OK)
        except self.model.DoesNotExist:
            return failure_response(f"{self.item_name} not found.", status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return failure_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            item = self.model.objects.get(pk=kwargs.get('pk'))
            serializer = self.serializer_class(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return success_response(f"{self.item_name} updated successfully.", serializer.data, status.HTTP_200_OK)
            else:
                return failure_response("Invalid data.", serializer.errors, status.HTTP_400_BAD_REQUEST)
        except self.model.DoesNotExist:
            return failure_response(f"{self.item_name} not found.", status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return failure_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            item = self.model.objects.get(pk=kwargs.get('pk'))
            item.delete()
            return success_response(f"{self.item_name} deleted successfully.", {}, status.HTTP_204_NO_CONTENT)
        except self.model.DoesNotExist:
            return failure_response(f"{self.item_name} not found.", status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return failure_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

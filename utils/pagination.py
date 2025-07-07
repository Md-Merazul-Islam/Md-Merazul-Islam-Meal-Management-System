from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status

# Custom Pagination Class
class CustomPagination(PageNumberPagination):
    page_size = 10  # Default number of items per page
    page_size_query_param = 'page_size'  # Allow clients to specify page size in the query params
    max_page_size = 100  # Maximum number of items per page


class BasePaginatedViewSet(viewsets.ModelViewSet):
    pagination_class = CustomPagination  # Use custom pagination

    def get_paginated_response(self, serializer):
        """Override this method to provide consistent pagination response."""
        return Response({
            "success": True,
            "statusCode": status.HTTP_200_OK,
            "message": "Paginated list",
            "data": serializer.data,
            "pagination": {
                "count": self.paginator.page.paginator.count,  # Total count of items
                "next": self.paginator.get_next_link(),  # Next page URL
                "previous": self.paginator.get_previous_link(),  # Previous page URL
            }
        })

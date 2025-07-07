
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

def success_response(message, data=None, status=status.HTTP_200_OK):
    return Response({
        "success": True,
        "statusCode": status,
        "message": message,
        "data": data
    }, status=status)


def failure_response(message, error=None, status=status.HTTP_400_BAD_REQUEST):
    return Response({
        "success": False,
        "statusCode": status,
        "message": message,
        "error": error
    }, status=status)

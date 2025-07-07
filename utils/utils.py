from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response


def failure_response(message, status=403):
    return Response({
        "success": False,
        "message": message,
        "data": {}
    }, status=status)


def success_response(data, message="Success", status=200):
    return Response({
        "success": True,
        "message": message,
        "data": data
    }, status=status)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, PermissionDenied):
        return failure_response("You do not have permission to perform this action.", status=403)

    return response

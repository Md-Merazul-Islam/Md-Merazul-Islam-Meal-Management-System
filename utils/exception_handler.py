from .utils import failure_response
from rest_framework.exceptions import PermissionDenied

from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if isinstance(exc, PermissionDenied):
        return failure_response("You do not have permission to perform this action.", status=403)

    return response
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import permissions

class IsAdminOrStaff(permissions.BasePermission):
    """
    Custom permission to allow access only to Admin or Staff users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff or
            request.user.is_superuser or
            getattr(request.user, 'role', None) == 'admin'
        )


class IsDeliveryManOrAdminOrStaff(permissions.BasePermission):
    """
    Custom permission to allow access only to Admin or Staff users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff or
            request.user.is_superuser or
            getattr(request.user, 'role', None) == 'admin' or
            getattr(request.user, 'role', None) == 'delivery_man'
        )


class IsAdminOrHasRoleAdmin(permissions.BasePermission):
    """
    Custom permission to allow only admin users or users with the 'admin' role
    to perform create, update, or delete operations.
    """

    def has_permission(self, request, view):
        # Allow GET requests for everyone (no authentication needed for reading data)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Ensure the user is authenticated for POST, PUT, DELETE requests
        if not request.user.is_authenticated:
            raise AuthenticationFailed(
                "You must be logged in to perform this action.")

        # Allow POST, PUT, DELETE only for Admin or Staff
        if request.user.is_staff or getattr(request.user, 'role', None) == 'admin':
            return True

        # If none of the conditions are met, deny access with a customized error message and status code
        raise PermissionDenied({
            'statusCode': 403,
            'success': True,
            'detail': 'You do not have permission to perform this action.'
        })

    def has_object_permission(self, request, view, obj):
        """
        Object-level permission check, used for specific object access control.
        """
        if request.user.is_staff or getattr(request.user, 'role', None) == 'admin':
            return True
        raise PermissionDenied({
            'statusCode': 403,
            'success': True,
            'detail': 'You do not have permission to perform this action.'
        })

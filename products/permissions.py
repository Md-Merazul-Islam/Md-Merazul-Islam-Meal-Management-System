# permissions.py
from rest_framework import permissions

from rest_framework.exceptions import AuthenticationFailed

class IsAdminOrHasRoleAdmin(permissions.BasePermission):
    """
    Custom permission to allow only admin users or users with the 'admin' role
    to perform create, update, or delete operations.
    """

    def has_permission(self, request, view):
        # Allow GET requests for everyone (no authentication needed for reading data)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check authentication for POST, PUT, DELETE requests
        if not request.user.is_authenticated:
            raise AuthenticationFailed(
                "You must be logged in to perform this action.")

        # Allow POST, PUT, DELETE only for Admin, Staff, or Teacher
        user = request.user
        if user.is_staff or getattr(user, 'role', None) in ['admin',]:
            return True
        return False

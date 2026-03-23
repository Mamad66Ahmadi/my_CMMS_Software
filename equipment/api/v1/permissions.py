# equipment/api/v1/permissions.py

from rest_framework import permissions

class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow staff users to create, edit, and delete objects,
    while allowing non-staff users to only read (safe methods).
    """
    def has_permission(self, request, view):
        # Allow safe methods (GET, HEAD, OPTIONS) for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow write methods (POST, PUT, PATCH, DELETE) only for staff users
        return request.user and request.user.is_staff
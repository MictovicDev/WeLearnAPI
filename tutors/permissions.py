from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsTutor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'tutor'
    

class IsTutorOwner(BasePermission):
    """Only the tutor that owns the profile."""
    def has_object_permission(self, request, view, obj):
        return hasattr(obj, 'user') and obj.user == request.user
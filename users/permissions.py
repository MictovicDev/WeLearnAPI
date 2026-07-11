from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'student'



class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        # obj can be a User or an object with a `user` attribute
        owner = getattr(obj, 'user', obj)
        return owner == request.user





class IsBookingParticipant(BasePermission):
    """Student or tutor involved in the booking."""
    def has_object_permission(self, request, view, obj):
        user = request.user
        return obj.student == user or obj.tutor_profile.user == user

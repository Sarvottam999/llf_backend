from rest_framework.permissions import BasePermission


class IsEngineer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'engineer'

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'admin'

class IsWorker(BasePermission):
    """Permission for Workers."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == "worker"


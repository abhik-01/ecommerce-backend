from rest_framework.permissions import BasePermission


class IsRole(BasePermission):
    """
    Allows access only to users with a specific role.
    Usage: permission_classes = [IsRole('admin')]
    """
    def __init__(self, role_name):
        self.role_name = role_name

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and hasattr(user, 'role') and user.role and user.role.role == self.role_name)


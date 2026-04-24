from rest_framework import permissions

class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to SuperAdmin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.has_role('SuperAdmin'))

class IsDeveloper(permissions.BasePermission):
    """
    Allows access only to Developer users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.has_role('Developer'))

class IsAdmin(permissions.BasePermission):
    """
    Allows access to SuperAdmin and Admin users.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        user_roles = request.user.role_names
        return any(role in ['SuperAdmin', 'Admin', 'Billing'] for role in user_roles)

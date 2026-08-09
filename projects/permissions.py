from rest_framework import permissions

from .models import ProjectMembership


def get_membership(user, project):
    if not user or not user.is_authenticated:
        return None
    return ProjectMembership.objects.filter(project=project, user=user).first()


def is_project_admin(user, project):
    if user.is_superuser:
        return True
    membership = get_membership(user, project)
    return bool(membership and membership.role == ProjectMembership.Role.ADMIN)


def is_project_member(user, project):
    if user.is_superuser:
        return True
    return get_membership(user, project) is not None


class IsProjectMember(permissions.BasePermission):
    """Object-level: user must belong to the project."""

    def has_object_permission(self, request, view, obj):
        project = obj if hasattr(obj, "memberships") else obj.project
        return is_project_member(request.user, project)


class IsProjectAdminOrReadOnly(permissions.BasePermission):
    """
    Any project member may read (GET/HEAD/OPTIONS).
    Only project admins (or the global superuser) may write.
    """

    def has_object_permission(self, request, view, obj):
        project = obj if hasattr(obj, "memberships") else obj.project
        if not is_project_member(request.user, project):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_project_admin(request.user, project)

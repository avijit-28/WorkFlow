from rest_framework import permissions

from projects.permissions import is_project_admin, is_project_member


class TaskPermission(permissions.BasePermission):
    """
    - Must be a member of the task's project to view it at all.
    - Project admins: full CRUD on any task in their project.
    - Regular members: can view all tasks in the project, and may
      update a task ONLY if it is assigned to them (status/progress
      updates handled at the view level restricting editable fields).
      Members cannot create, delete, or reassign tasks.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        project = obj.project
        if not is_project_member(request.user, project):
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if is_project_admin(request.user, project):
            return True

        # Non-admin members may only PATCH/PUT a task assigned to them
        # (never DELETE, never create -- create is blocked at list level).
        if request.method in ("PATCH", "PUT"):
            return obj.assigned_to_id == request.user.id

        return False

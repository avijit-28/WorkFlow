from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.exceptions import PermissionDenied

from projects.models import Project, ProjectMembership
from projects.permissions import is_project_admin, is_project_member

from .models import Task
from .permissions import TaskPermission
from .serializers import TaskSerializer, TaskStatusUpdateSerializer
from notifications.models import Notification

User = get_user_model()


def _notify_assignment(actor, task):
    """Notify a task's assignee, unless they assigned it to themselves."""
    if task.assigned_to_id and task.assigned_to_id != actor.id:
        Notification.objects.create(
            recipient_id=task.assigned_to_id,
            verb=Notification.Verb.TASK_ASSIGNED,
            message=f'{actor.username} assigned you to "{task.title}" in {task.project.name}',
            project=task.project,
            task=task,
        )


def _notify_status_change(actor, task):
    """
    A task's status just changed. Tell the "other side":
      - if the assignee themself moved it, notify the project's admin(s)
      - if an admin (or anyone else) moved it, notify the assignee
    """
    message = f'{actor.username} moved "{task.title}" to {task.get_status_display()}'

    if task.assigned_to_id == actor.id:
        admin_ids = (
            ProjectMembership.objects.filter(project=task.project, role=ProjectMembership.Role.ADMIN)
            .exclude(user_id=actor.id)
            .values_list("user_id", flat=True)
        )
        Notification.objects.bulk_create(
            [
                Notification(
                    recipient_id=uid,
                    verb=Notification.Verb.TASK_STATUS_CHANGED,
                    message=message,
                    project=task.project,
                    task=task,
                )
                for uid in admin_ids
            ]
        )
    elif task.assigned_to_id and task.assigned_to_id != actor.id:
        Notification.objects.create(
            recipient_id=task.assigned_to_id,
            verb=Notification.Verb.TASK_STATUS_CHANGED,
            message=message,
            project=task.project,
            task=task,
        )


class TaskViewSet(viewsets.ModelViewSet):
    """
    /api/tasks/?project=<id>&status=todo&assigned_to=<id>&overdue=true&mine=true
    """

    permission_classes = [permissions.IsAuthenticated, TaskPermission]
    serializer_class = TaskSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            qs = Task.objects.all()
        else:
            member_project_ids = ProjectMembership.objects.filter(user=user).values_list(
                "project_id", flat=True
            )
            qs = Task.objects.filter(project_id__in=member_project_ids)

        params = self.request.query_params
        if project_id := params.get("project"):
            qs = qs.filter(project_id=project_id)
        if status_ := params.get("status"):
            qs = qs.filter(status=status_)
        if assigned_to := params.get("assigned_to"):
            qs = qs.filter(assigned_to_id=assigned_to)
        if params.get("mine") == "true":
            qs = qs.filter(assigned_to=user)
        if params.get("overdue") == "true":
            qs = qs.filter(due_date__lt=timezone.now()).exclude(status=Task.Status.DONE)
        return qs.select_related("project", "assigned_to", "created_by")

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        if not is_project_admin(self.request.user, project):
            raise PermissionDenied("Only a project admin can create tasks in this project.")
        task = serializer.save(created_by=self.request.user)
        _notify_assignment(self.request.user, task)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()  # runs object-level permission check
        partial = kwargs.pop("partial", False)
        previous_assignee_id = instance.assigned_to_id
        previous_status = instance.status

        if is_project_admin(request.user, instance.project) or request.user.is_superuser:
            serializer = TaskSerializer(instance, data=request.data, partial=partial, context={"request": request})
        else:
            # Regular member editing their own assigned task: status/priority only.
            serializer = TaskStatusUpdateSerializer(instance, data=request.data, partial=partial)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        if instance.assigned_to_id != previous_assignee_id:
            _notify_assignment(request.user, instance)
        if instance.status != previous_status:
            _notify_status_change(request.user, instance)

        return Response(TaskSerializer(instance, context={"request": request}).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not (is_project_admin(request.user, instance.project) or request.user.is_superuser):
            return Response(
                {"detail": "Only a project admin can delete tasks."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class DashboardView(APIView):
    """
    GET /api/dashboard/
    Returns a summary of the current user's tasks and projects:
    counts by status, overdue tasks, and per-project breakdowns.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.is_superuser:
            projects = Project.objects.all()
            all_tasks = Task.objects.all()
        else:
            projects = Project.objects.filter(memberships__user=user).distinct()
            all_tasks = Task.objects.filter(project__in=projects)

        my_tasks = Task.objects.filter(assigned_to=user)
        now = timezone.now()

        my_status_counts = {
            row["status"]: row["count"] for row in my_tasks.values("status").annotate(count=Count("id"))
        }
        overdue_qs = all_tasks.filter(due_date__lt=now).exclude(status=Task.Status.DONE)
        my_overdue_qs = my_tasks.filter(due_date__lt=now).exclude(status=Task.Status.DONE)

        project_breakdown = []
        for project in projects:
            project_tasks = all_tasks.filter(project=project)
            status_counts = {
                row["status"]: row["count"]
                for row in project_tasks.values("status").annotate(count=Count("id"))
            }
            project_breakdown.append(
                {
                    "project_id": project.id,
                    "project_name": project.name,
                    "total_tasks": project_tasks.count(),
                    "status_counts": status_counts,
                    "overdue_count": project_tasks.filter(due_date__lt=now)
                    .exclude(status=Task.Status.DONE)
                    .count(),
                }
            )

        def brief(qs):
            return [
                {
                    "id": t.id,
                    "title": t.title,
                    "project": t.project.name,
                    "project_id": t.project_id,
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": t.due_date,
                }
                for t in qs.select_related("project")[:20]
            ]

        return Response(
            {
                "summary": {
                    "total_projects": projects.count(),
                    "my_total_tasks": my_tasks.count(),
                    "my_status_counts": my_status_counts,
                    "my_overdue_count": my_overdue_qs.count(),
                    "org_total_tasks": all_tasks.count(),
                    "org_overdue_count": overdue_qs.count(),
                },
                "my_overdue_tasks": brief(my_overdue_qs.order_by("due_date")),
                "my_upcoming_tasks": brief(
                    my_tasks.filter(due_date__gte=now).exclude(status=Task.Status.DONE).order_by("due_date")
                ),
                "projects": project_breakdown,
            }
        )

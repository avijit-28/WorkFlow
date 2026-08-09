from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.serializers import UserSerializer
from projects.models import Project, ProjectMembership

from .models import Task

User = get_user_model()


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="assigned_to", write_only=True, required=False, allow_null=True
    )
    created_by = UserSerializer(read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "project_name",
            "title",
            "description",
            "status",
            "priority",
            "assigned_to",
            "assigned_to_id",
            "created_by",
            "due_date",
            "is_overdue",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "completed_at"]

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Task title cannot be blank.")
        return value.strip()

    def validate(self, attrs):
        project = attrs.get("project") or getattr(self.instance, "project", None)
        assigned_to = attrs.get("assigned_to")
        if project and assigned_to:
            if not ProjectMembership.objects.filter(project=project, user=assigned_to).exists():
                raise serializers.ValidationError(
                    {"assigned_to_id": "User must be a member of the project to be assigned this task."}
                )
        return attrs


class TaskStatusUpdateSerializer(serializers.ModelSerializer):
    """Restricted serializer used for members updating only their own task's status/priority."""

    class Meta:
        model = Task
        fields = ["id", "status", "priority"]
        read_only_fields = ["id"]

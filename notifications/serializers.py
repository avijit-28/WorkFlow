from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    task_title = serializers.CharField(source="task.title", read_only=True, default=None)
    kind = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "kind",
            "verb",
            "message",
            "project",
            "project_name",
            "task",
            "task_title",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields

    def get_kind(self, obj):
        return "notification"

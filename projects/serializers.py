from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import Project, ProjectMembership

User = get_user_model()


class ProjectMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )

    class Meta:
        model = ProjectMembership
        fields = ["id", "user", "user_id", "role", "joined_at"]
        read_only_fields = ["id", "joined_at"]


class ProjectSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "created_by",
            "member_count",
            "task_count",
            "my_role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Project name cannot be blank.")
        return value.strip()

    def get_member_count(self, obj):
        return obj.memberships.count()

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_my_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user).first()
        return membership.role if membership else None


class ProjectDetailSerializer(ProjectSerializer):
    memberships = ProjectMembershipSerializer(many=True, read_only=True)

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + ["memberships"]

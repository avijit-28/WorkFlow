from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import MAX_UPLOAD_BYTES, ProjectSubmission


class ProjectSubmissionSerializer(serializers.ModelSerializer):
    member = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSubmission
        fields = [
            "id",
            "project",
            "member",
            "file",
            "file_url",
            "file_name",
            "file_size",
            "repo_link",
            "live_link",
            "description",
            "submitted_at",
            "updated_at",
        ]
        read_only_fields = ["id", "member", "submitted_at", "updated_at"]
        extra_kwargs = {"file": {"write_only": True, "required": False}}

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url

    def get_file_name(self, obj):
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else None

    def get_file_size(self, obj):
        try:
            return obj.file.size if obj.file else None
        except (FileNotFoundError, ValueError):
            return None

    def validate_file(self, value):
        if value and value.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("File must be 1GB or smaller.")
        return value

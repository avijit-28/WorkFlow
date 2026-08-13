import mimetypes

from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import DirectMessage, ProjectMessage

ALLOWED_ATTACHMENT_PREFIXES = ("image/", "video/")


def _attachment_type(file_field):
    if not file_field:
        return None
    guessed, _ = mimetypes.guess_type(file_field.name)
    if guessed and guessed.startswith("video/"):
        return "video"
    return "image"


def _validate_attachment_kind(value):
    if not value:
        return value
    guessed, _ = mimetypes.guess_type(value.name)
    if not guessed or not guessed.startswith(ALLOWED_ATTACHMENT_PREFIXES):
        raise serializers.ValidationError("Only image or video attachments are allowed.")
    return value


class ProjectMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    attachment_url = serializers.SerializerMethodField()
    attachment_type = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMessage
        fields = [
            "id", "project", "sender", "content",
            "attachment", "attachment_url", "attachment_type", "created_at",
        ]
        read_only_fields = ["id", "sender", "created_at"]
        extra_kwargs = {"attachment": {"write_only": True, "required": False}}

    def validate_attachment(self, value):
        return _validate_attachment_kind(value)

    def validate_content(self, value):
        return (value or "").strip()

    def validate(self, attrs):
        content = attrs.get("content", "")
        attachment = attrs.get("attachment")
        if not content and not attachment:
            raise serializers.ValidationError("Message needs text or an attachment.")
        return attrs

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        request = self.context.get("request")
        url = obj.attachment.url
        return request.build_absolute_uri(url) if request else url

    def get_attachment_type(self, obj):
        return _attachment_type(obj.attachment)


class DirectMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    recipient_id = serializers.IntegerField(write_only=True)
    attachment_url = serializers.SerializerMethodField()
    attachment_type = serializers.SerializerMethodField()

    class Meta:
        model = DirectMessage
        fields = [
            "id", "sender", "recipient", "recipient_id", "content",
            "attachment", "attachment_url", "attachment_type", "created_at", "read_at",
        ]
        read_only_fields = ["id", "sender", "recipient", "created_at", "read_at"]
        extra_kwargs = {"attachment": {"write_only": True, "required": False}}

    def validate_attachment(self, value):
        return _validate_attachment_kind(value)

    def validate_content(self, value):
        return (value or "").strip()

    def validate(self, attrs):
        content = attrs.get("content", "")
        attachment = attrs.get("attachment")
        if not content and not attachment:
            raise serializers.ValidationError("Message needs text or an attachment.")
        return attrs

    def validate_recipient_id(self, value):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Recipient not found.")
        return value

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        request = self.context.get("request")
        url = obj.attachment.url
        return request.build_absolute_uri(url) if request else url

    def get_attachment_type(self, obj):
        return _attachment_type(obj.attachment)

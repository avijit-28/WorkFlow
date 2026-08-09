from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import DirectMessage, ProjectMessage


class ProjectMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = ProjectMessage
        fields = ["id", "project", "sender", "content", "created_at"]
        read_only_fields = ["id", "sender", "created_at"]

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        return value.strip()


class DirectMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    recipient_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = DirectMessage
        fields = ["id", "sender", "recipient", "recipient_id", "content", "created_at", "read_at"]
        read_only_fields = ["id", "sender", "recipient", "created_at", "read_at"]

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        return value.strip()

    def validate_recipient_id(self, value):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Recipient not found.")
        return value

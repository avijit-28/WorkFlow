from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def _validate_chat_attachment_size(value):
    max_bytes = 25 * 1024 * 1024  # 25MB, plenty for phone photos/short clips
    if value.size > max_bytes:
        raise ValidationError("Attachments must be 25MB or smaller.")


def project_attachment_upload_path(instance, filename):
    return f"chat/project_{instance.project_id}/{filename}"


def direct_attachment_upload_path(instance, filename):
    return f"chat/dm_{instance.sender_id}_{instance.recipient_id}/{filename}"


class ProjectMessage(models.Model):
    """Group chat scoped to a project. Any member (incl. the admin) can post/read."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_messages"
    )
    content = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to=project_attachment_upload_path, blank=True, null=True, validators=[_validate_chat_attachment_size]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.project_id}] {self.sender.username}: {self.content[:30]}"


class DirectMessage(models.Model):
    """
    A 1-on-1 message between any two users in the system -- covers
    both a private member<->admin thread and general user<->user chat.
    """

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_messages"
    )
    content = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to=direct_attachment_upload_path, blank=True, null=True, validators=[_validate_chat_attachment_size]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username}: {self.content[:30]}"

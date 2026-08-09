from django.conf import settings
from django.db import models


class ProjectMessage(models.Model):
    """Group chat scoped to a project. Any member (incl. the admin) can post/read."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_messages"
    )
    content = models.TextField()
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
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username}: {self.content[:30]}"

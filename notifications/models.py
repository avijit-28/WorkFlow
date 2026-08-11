from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    A real, persisted notification for a discrete event (currently:
    being assigned to a task). "Due soon" reminders are NOT stored
    here -- they're computed on the fly in the API view from live
    task data, so no background/cron job is required to keep them
    accurate.
    """

    class Verb(models.TextChoices):
        TASK_ASSIGNED = "task_assigned", "Assigned to a task"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    verb = models.CharField(max_length=30, choices=Verb.choices)
    message = models.CharField(max_length=255)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    task = models.ForeignKey(
        "tasks.Task", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient.username}: {self.message}"

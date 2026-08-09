from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

MAX_UPLOAD_BYTES = 1024 * 1024 * 1024  # 1 GB


def validate_file_size(file):
    if file.size > MAX_UPLOAD_BYTES:
        raise ValidationError("File must be 1GB or smaller.")


def submission_upload_path(instance, filename):
    return f"submissions/project_{instance.project_id}/user_{instance.member_id}/{filename}"


class ProjectSubmission(models.Model):
    """
    A member's deliverable for a project: an optional uploaded file
    (<=1GB), a repo/source link, an optional live demo link, and a
    description. One submission per (project, member) -- resubmitting
    updates it rather than creating a new row.
    """

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="submissions"
    )
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions"
    )
    file = models.FileField(
        upload_to=submission_upload_path, blank=True, null=True, validators=[validate_file_size]
    )
    repo_link = models.URLField(blank=True, help_text="e.g. GitHub repository URL")
    live_link = models.URLField(blank=True, help_text="Optional live/deployed demo URL")
    description = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("project", "member")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.member.username} -> {self.project.name}"

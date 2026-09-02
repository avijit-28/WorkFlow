from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_projects"
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="ProjectMembership", related_name="projects"
    )
    admin_only_chat = models.BooleanField(
        default=False,
        help_text="If true, only project admins may post in this project's group chat.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def clean(self):
        if not self.name or not self.name.strip():
            raise ValidationError({"name": "Project name cannot be blank."})


class ProjectMembership(models.Model):
    """Per-project role. A user can be 'admin' in one project and
    just a 'member' in another, independent of their global role."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "user")
        ordering = ["-role", "joined_at"]

    def __str__(self):
        return f"{self.user.username} in {self.project.name} ({self.role})"

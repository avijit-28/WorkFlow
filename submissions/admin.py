from django.contrib import admin

from .models import ProjectSubmission


@admin.register(ProjectSubmission)
class ProjectSubmissionAdmin(admin.ModelAdmin):
    list_display = ["project", "member", "repo_link", "live_link", "updated_at"]

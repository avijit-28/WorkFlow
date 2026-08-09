from django.contrib import admin

from .models import DirectMessage, ProjectMessage


@admin.register(ProjectMessage)
class ProjectMessageAdmin(admin.ModelAdmin):
    list_display = ["project", "sender", "created_at"]


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ["sender", "recipient", "created_at", "read_at"]

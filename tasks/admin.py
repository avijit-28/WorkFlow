from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "status", "priority", "assigned_to", "due_date", "is_overdue"]
    list_filter = ["status", "priority"]
    search_fields = ["title"]

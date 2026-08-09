from django.contrib import admin

from .models import Project, ProjectMembership


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at"]
    search_fields = ["name"]
    inlines = [ProjectMembershipInline]


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ["project", "user", "role", "joined_at"]
    list_filter = ["role"]

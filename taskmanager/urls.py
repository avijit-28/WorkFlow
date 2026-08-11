from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import include, path
from django.views.static import serve as serve_media

from tasks.views import DashboardView


def frontend(request):
    """Serves the single-page app UI."""
    return render(request, "index.html")


def api_root(request):
    return JsonResponse(
        {
            "status": "ok",
            "message": "Task Manager API",
            "endpoints": {
                "admin": "/admin/",
                "signup": "/api/auth/signup/",
                "login": "/api/auth/login/",
                "refresh": "/api/auth/login/refresh/",
                "me": "/api/auth/me/",
                "users": "/api/auth/users/",
                "projects": "/api/projects/",
                "tasks": "/api/tasks/",
                "dashboard": "/api/dashboard/",
                "submissions": "/api/submissions/?project=<id>",
                "project_messages": "/api/chat/project-messages/?project=<id>",
                "direct_messages": "/api/chat/direct-messages/?with=<user_id>",
                "conversations": "/api/chat/conversations/",
                "notifications": "/api/notifications/",
                "password_change": "/api/auth/password/change/",
                "password_reset": "/api/auth/password/reset/",
                "password_reset_confirm": "/api/auth/password/reset/confirm/",
            },
        }
    )


def health_check(request):
    return JsonResponse({"status": "healthy"})


urlpatterns = [
    path("", frontend, name="frontend"),
    path("api/", api_root, name="api-root"),
    path("health/", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/projects/", include("projects.urls")),
    path("api/tasks/", include("tasks.urls")),
    path("api/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("api/submissions/", include("submissions.urls")),
    path("api/chat/", include("chat.urls")),
    path("api/notifications/", include("notifications.urls")),
]

# Media (uploaded submission files) are served by Django directly --
# unconditionally, not just when DEBUG=True -- so downloads work on
# this single-dyno deploy. Note: Railway's filesystem is ephemeral
# across deploys/restarts (see README); swap in S3/R2 if files need
# to survive redeploys.
urlpatterns += [
    path("media/<path:path>", serve_media, {"document_root": settings.MEDIA_ROOT}),
]

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from tasks.models import Task

from .models import Notification
from .serializers import NotificationSerializer

DUE_SOON_WINDOW_HOURS = 24


def _due_soon_items(user):
    """Tasks assigned to `user`, due within the next DUE_SOON_WINDOW_HOURS,
    not already overdue, and not done. Computed live -- nothing stored."""
    now = timezone.now()
    horizon = now + timedelta(hours=DUE_SOON_WINDOW_HOURS)
    tasks = (
        Task.objects.filter(assigned_to=user, due_date__gte=now, due_date__lte=horizon)
        .exclude(status=Task.Status.DONE)
        .select_related("project")
        .order_by("due_date")
    )
    return [
        {
            "id": f"duesoon-{t.id}",
            "kind": "due_soon",
            "verb": "due_soon",
            "message": f'"{t.title}" is due soon',
            "project": t.project_id,
            "project_name": t.project.name,
            "task": t.id,
            "task_title": t.title,
            "is_read": False,
            "created_at": t.due_date,
        }
        for t in tasks
    ]


class NotificationListView(APIView):
    """
    GET /api/notifications/
    Real notifications (task assignments) merged with live-computed
    "due soon" reminders, newest first.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        real = NotificationSerializer(
            Notification.objects.filter(recipient=request.user)[:40], many=True
        ).data
        due_soon = _due_soon_items(request.user)
        combined = list(real) + due_soon

        def sort_key(n):
            created = n["created_at"]
            return parse_datetime(created) if isinstance(created, str) else created

        combined.sort(key=sort_key, reverse=True)
        return Response(combined)


class UnreadCountView(APIView):
    """GET /api/notifications/unread-count/ -- for badges."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False).count()
        due_soon_count = len(_due_soon_items(request.user))
        return Response({"unread_notifications": unread_notifications, "due_soon": due_soon_count})


class MarkNotificationReadView(APIView):
    """POST /api/notifications/{id}/read/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class MarkAllNotificationsReadView(APIView):
    """POST /api/notifications/read-all/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"marked_read": updated})

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.permissions import is_project_admin, is_project_member
from notifications.models import Notification

from .models import DirectMessage, ProjectMessage
from .serializers import DirectMessageSerializer, ProjectMessageSerializer

User = get_user_model()


def _notify_project_message(message):
    """Notify every other member of the project (not the sender)."""
    from projects.models import ProjectMembership

    recipient_ids = ProjectMembership.objects.filter(project=message.project).exclude(
        user_id=message.sender_id
    ).values_list("user_id", flat=True)

    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=uid,
                verb=Notification.Verb.PROJECT_MESSAGE,
                message=f'{message.sender.username} in {message.project.name}: "{message.content[:60]}"',
                project=message.project,
            )
            for uid in recipient_ids
        ]
    )


def _notify_direct_message(message):
    Notification.objects.create(
        recipient_id=message.recipient_id,
        verb=Notification.Verb.DIRECT_MESSAGE,
        message=f'{message.sender.username} messaged you: "{message.content[:60]}"',
    )


class ProjectMessageListCreateView(generics.ListCreateAPIView):
    """
    /api/chat/project-messages/?project=<id>
    GET  -- list all messages in a project (must be a member)
    POST -- post a message to a project (must be a member); body: {"project": <id>, "content": "..."}
    """

    serializer_class = ProjectMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get("project")
        if not project_id:
            return ProjectMessage.objects.none()
        return ProjectMessage.objects.filter(project_id=project_id).select_related("sender", "project")

    def list(self, request, *args, **kwargs):
        project_id = request.query_params.get("project")
        if not project_id:
            return Response({"detail": "project query param is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not self._is_member(request.user, project_id):
            return Response({"detail": "You are not a member of this project."}, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        project_id = request.data.get("project")
        if not project_id:
            return Response({"detail": "project is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not self._is_member(request.user, project_id):
            return Response({"detail": "You are not a member of this project."}, status=status.HTTP_403_FORBIDDEN)
        if not self._can_post(request.user, project_id):
            return Response(
                {"detail": "Only project admins can send messages in this group chat."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(sender=request.user, project_id=project_id)
        _notify_project_message(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _is_member(user, project_id):
        from projects.models import Project

        project = Project.objects.filter(id=project_id).first()
        if not project:
            return False
        return is_project_member(user, project) or user.is_superuser

    @staticmethod
    def _can_post(user, project_id):
        from projects.models import Project

        project = Project.objects.filter(id=project_id).first()
        if not project:
            return False
        if not project.admin_only_chat:
            return True
        return is_project_admin(user, project) or user.is_superuser


class DirectMessageListCreateView(generics.ListCreateAPIView):
    """
    /api/chat/direct-messages/?with=<user_id>
    GET  -- the full thread between the current user and `with`
    POST -- send a message; body: {"recipient_id": <id>, "content": "..."}
    Any authenticated user may message any other user.
    """

    serializer_class = DirectMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        other_id = self.request.query_params.get("with")
        user = self.request.user
        if not other_id:
            return DirectMessage.objects.none()
        qs = DirectMessage.objects.filter(
            Q(sender=user, recipient_id=other_id) | Q(sender_id=other_id, recipient=user)
        ).select_related("sender", "recipient")
        # mark incoming messages as read as they're viewed
        DirectMessage.objects.filter(sender_id=other_id, recipient=user, read_at__isnull=True).update(
            read_at=_now()
        )
        return qs

    def list(self, request, *args, **kwargs):
        if not request.query_params.get("with"):
            return Response({"detail": "'with' query param (user id) is required."}, status=status.HTTP_400_BAD_REQUEST)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipient_id = serializer.validated_data["recipient_id"]
        if recipient_id == request.user.id:
            return Response({"detail": "You cannot message yourself."}, status=status.HTTP_400_BAD_REQUEST)
        message = serializer.save(sender=request.user, recipient_id=recipient_id)
        _notify_direct_message(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


def _now():
    from django.utils import timezone

    return timezone.now()


def _attachment_type_for(message):
    if not message.attachment:
        return None
    from .serializers import _attachment_type

    return _attachment_type(message.attachment)


class ConversationListView(APIView):
    """
    GET /api/chat/conversations/
    Returns every user the current user has exchanged a DM with,
    the most recent message, and how many are unread.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from accounts.serializers import UserSerializer

        user = request.user
        partner_ids = set(
            DirectMessage.objects.filter(sender=user).values_list("recipient_id", flat=True)
        ) | set(DirectMessage.objects.filter(recipient=user).values_list("sender_id", flat=True))

        results = []
        for pid in partner_ids:
            last = (
                DirectMessage.objects.filter(
                    Q(sender=user, recipient_id=pid) | Q(sender_id=pid, recipient=user)
                )
                .order_by("-created_at")
                .first()
            )
            unread = DirectMessage.objects.filter(sender_id=pid, recipient=user, read_at__isnull=True).count()
            other = User.objects.filter(id=pid).first()
            if not other or not last:
                continue
            results.append(
                {
                    "user": UserSerializer(other, context={"request": request}).data,
                    "last_message": last.content,
                    "last_message_attachment_type": _attachment_type_for(last),
                    "last_message_at": last.created_at,
                    "unread_count": unread,
                }
            )
        results.sort(key=lambda r: r["last_message_at"], reverse=True)
        return Response(results)

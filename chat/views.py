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
        return (
            ProjectMessage.objects.filter(project_id=project_id)
            .exclude(hidden_for=self.request.user)
            .select_related("sender", "project")
        )

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


class ProjectMessageDetailView(generics.DestroyAPIView):
    """
    DELETE /api/chat/project-messages/<id>/
    "Delete for everyone" -- only the original sender (or a superuser) may
    do this. It permanently removes the message for every member.
    """

    queryset = ProjectMessage.objects.all()
    serializer_class = ProjectMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        message = self.get_object()
        if message.sender_id != request.user.id and not request.user.is_superuser:
            return Response(
                {"detail": "You can only delete your own messages for everyone."},
                status=status.HTTP_403_FORBIDDEN,
            )
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectMessageHideView(APIView):
    """
    POST /api/chat/project-messages/hide/   body: {"ids": [1, 2, 3]}
    "Delete for me" -- any project member can hide ANY message (their own
    or someone else's) from their own chat view only. Everyone else still
    sees it untouched. Group chat only, supports multiple ids at once.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids (a non-empty list) is required."}, status=status.HTTP_400_BAD_REQUEST)

        messages = ProjectMessage.objects.filter(id__in=ids).select_related("project")
        hidden_ids = []
        for message in messages:
            if is_project_member(request.user, message.project) or request.user.is_superuser:
                message.hidden_for.add(request.user)
                hidden_ids.append(message.id)
        return Response({"hidden_ids": hidden_ids})


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
        ).exclude(hidden_for=user).select_related("sender", "recipient")
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


class DirectMessageDetailView(generics.DestroyAPIView):
    """
    DELETE /api/chat/direct-messages/<id>/
    Only the original sender (or a superuser) can delete their own message
    for everyone -- it disappears from both people's threads.
    """

    queryset = DirectMessage.objects.all()
    serializer_class = DirectMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        message = self.get_object()
        if message.sender_id != request.user.id and not request.user.is_superuser:
            return Response(
                {"detail": "You can only delete your own messages."},
                status=status.HTTP_403_FORBIDDEN,
            )
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DirectMessageHideView(APIView):
    """
    POST /api/chat/direct-messages/hide/   body: {"ids": [1, 2, 3]}
    "Delete for me" -- either side of a DM thread can hide ANY message
    (their own or the other person's) from their own view only. The other
    person's thread is completely unaffected.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids (a non-empty list) is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        messages = DirectMessage.objects.filter(id__in=ids).filter(Q(sender=user) | Q(recipient=user))
        hidden_ids = []
        for message in messages:
            message.hidden_for.add(user)
            hidden_ids.append(message.id)
        return Response({"hidden_ids": hidden_ids})


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

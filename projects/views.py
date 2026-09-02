from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Project, ProjectMembership
from .permissions import IsProjectAdminOrReadOnly, is_project_admin
from .serializers import ProjectDetailSerializer, ProjectMembershipSerializer, ProjectSerializer
from notifications.models import Notification

User = get_user_model()


class ProjectViewSet(viewsets.ModelViewSet):
    """
    /api/projects/                      GET (list mine), POST (create)
    /api/projects/{id}/                 GET, PATCH, PUT, DELETE
    /api/projects/{id}/members/         GET (list), POST (add member) - admin only to add
    /api/projects/{id}/members/{uid}/   PATCH (change role), DELETE (remove) - admin only
    """

    permission_classes = [permissions.IsAuthenticated, IsProjectAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_global_admin:
            return Project.objects.all()
        return Project.objects.filter(memberships__user=user).distinct()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProjectDetailSerializer
        return ProjectSerializer

    def create(self, request, *args, **kwargs):
        if not (request.user.is_global_admin or request.user.is_superuser):
            return Response(
                {"detail": "Only an admin can create projects."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        project = serializer.save(created_by=self.request.user)
        # Creator automatically becomes the project's admin.
        ProjectMembership.objects.create(
            project=project, user=self.request.user, role=ProjectMembership.Role.ADMIN
        )

    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        if not is_project_admin(request.user, project):
            return Response(
                {"detail": "Only a project admin can delete this project."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        project = self.get_object()

        if request.method == "GET":
            memberships = project.memberships.select_related("user").all()
            return Response(ProjectMembershipSerializer(memberships, many=True).data)

        # POST -- add a member. Admins only.
        if not is_project_admin(request.user, project):
            return Response(
                {"detail": "Only a project admin can add members."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ProjectMembershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        role = serializer.validated_data.get("role", ProjectMembership.Role.MEMBER)
        membership, created = ProjectMembership.objects.get_or_create(
            project=project, user=user, defaults={"role": role}
        )
        if not created:
            return Response(
                {"detail": "User is already a member of this project."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.id != request.user.id:
            Notification.objects.create(
                recipient=user,
                verb=Notification.Verb.MEMBER_ADDED,
                message=f'{request.user.username} added you to "{project.name}"',
                project=project,
            )
        return Response(ProjectMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch", "delete"], url_path=r"members/(?P<user_id>\d+)")
    def member_detail(self, request, pk=None, user_id=None):
        project = self.get_object()

        if not is_project_admin(request.user, project):
            return Response(
                {"detail": "Only a project admin can modify membership."},
                status=status.HTTP_403_FORBIDDEN,
            )

        membership = get_object_or_404(ProjectMembership, project=project, user_id=user_id)

        if request.method == "DELETE":
            if membership.user_id == project.created_by_id:
                return Response(
                    {"detail": "Cannot remove the project owner."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            membership.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH -- change role
        role = request.data.get("role")
        if role not in ProjectMembership.Role.values:
            return Response({"detail": "Invalid role."}, status=status.HTTP_400_BAD_REQUEST)
        membership.role = role
        membership.save()
        return Response(ProjectMembershipSerializer(membership).data)

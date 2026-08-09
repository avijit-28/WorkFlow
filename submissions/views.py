from rest_framework import permissions, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from projects.models import ProjectMembership
from projects.permissions import is_project_admin

from .models import ProjectSubmission
from .serializers import ProjectSubmissionSerializer


class ProjectSubmissionViewSet(viewsets.ModelViewSet):
    """
    /api/submissions/?project=<id>   GET (list), POST (create/update your own -- upsert)
    /api/submissions/{id}/           GET, PATCH, DELETE

    - A member can only ever have ONE submission per project; POSTing
      again just updates their existing one.
    - Project admins can see everyone's submission in their project.
    - Regular members can only see their own submission.
    """

    serializer_class = ProjectSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        qs = ProjectSubmission.objects.select_related("project", "member")
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)

        if user.is_superuser:
            return qs

        member_project_ids = ProjectMembership.objects.filter(user=user).values_list(
            "project_id", flat=True
        )
        return qs.filter(project_id__in=member_project_ids)

    def _visible_qs(self, qs):
        """Restrict rows to: admin sees all in their admin projects, else only own."""
        user = self.request.user
        if user.is_superuser:
            return qs
        admin_project_ids = ProjectMembership.objects.filter(
            user=user, role=ProjectMembership.Role.ADMIN
        ).values_list("project_id", flat=True)
        from django.db.models import Q

        return qs.filter(Q(project_id__in=admin_project_ids) | Q(member=user))

    def list(self, request, *args, **kwargs):
        qs = self._visible_qs(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def perform_create_or_update(self, request):
        project_id = request.data.get("project")
        if not project_id:
            return None, Response({"detail": "project is required."}, status=status.HTTP_400_BAD_REQUEST)

        member_exists = ProjectMembership.objects.filter(project_id=project_id, user=request.user).exists()
        if not (member_exists or request.user.is_superuser):
            return None, Response(
                {"detail": "You must be a member of this project to submit."},
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = ProjectSubmission.objects.filter(project_id=project_id, member=request.user).first()
        serializer = self.get_serializer(instance, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(project_id=project_id, member=request.user)
        return serializer, None

    def create(self, request, *args, **kwargs):
        serializer, error_response = self.perform_create_or_update(request)
        if error_response:
            return error_response
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.member_id != request.user.id and not request.user.is_superuser:
            return Response(
                {"detail": "You can only edit your own submission."}, status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(
            instance, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        allowed = instance.member_id == request.user.id or is_project_admin(request.user, instance.project) or request.user.is_superuser
        if not allowed:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

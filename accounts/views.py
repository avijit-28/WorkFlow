from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SignupSerializer,
    UserSerializer,
)

User = get_user_model()
_reset_token_generator = PasswordResetTokenGenerator()


class SignupView(generics.CreateAPIView):
    """POST /api/auth/signup/ -- open to anyone."""

    queryset = User.objects.all()
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ -- returns access + refresh JWT tokens."""

    serializer_class = CustomTokenObtainPairSerializer


class MeView(APIView):
    """GET/PATCH /api/auth/me/ -- current authenticated user's profile."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserListView(generics.ListAPIView):
    """GET /api/auth/users/ -- list all users (for assigning tasks / adding members)."""

    queryset = User.objects.all().order_by("username")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChangePasswordView(APIView):
    """POST /api/auth/password/change/ -- change your own password while logged in."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password changed successfully."})


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password/reset/ -- body: {"email": "..."}
    Always responds with the same generic message whether or not the
    email exists, so this endpoint can't be used to enumerate accounts.
    In dev, EMAIL_BACKEND defaults to the console backend, so the reset
    link is printed to the server's terminal instead of actually
    emailed -- see README for wiring up real SMTP in production.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = _reset_token_generator.make_token(user)
            reset_link = f"{request.scheme}://{request.get_host()}/?reset_uid={uid}&reset_token={token}"
            send_mail(
                subject="Reset your Task Manager password",
                message=(
                    f"Hi {user.username},\n\n"
                    f"Click the link below to set a new password:\n{reset_link}\n\n"
                    "If you didn't request this, you can ignore this email."
                ),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )

        return Response({"detail": "If that email is registered, a reset link has been sent."})


class PasswordResetConfirmView(APIView):
    """POST /api/auth/password/reset/confirm/ -- body: {"uid", "token", "new_password", "new_password2"}"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            user_id = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not _reset_token_generator.check_token(user, data["token"]):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password has been reset. You can log in now."})

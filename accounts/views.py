from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import CustomTokenObtainPairSerializer, SignupSerializer, UserSerializer

User = get_user_model()


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

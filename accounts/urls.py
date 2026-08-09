from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, MeView, SignupView, UserListView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("login/refresh/", TokenRefreshView.as_view(), name="login-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("users/", UserListView.as_view(), name="user-list"),
]

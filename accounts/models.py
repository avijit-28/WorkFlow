from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model.

    `role` is the user's GLOBAL role in the system:
      - admin  : can create projects (becoming that project's admin
                 automatically) and has broader visibility.
      - member : regular user. What they can do inside a given
                 project is governed by ProjectMembership.role
                 (admin/member) in the `projects` app — a user can
                 be an admin of one project and a plain member of
                 another, regardless of this global role.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_global_admin(self):
        return self.role == self.Role.ADMIN

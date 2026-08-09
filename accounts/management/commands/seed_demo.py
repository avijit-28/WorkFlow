from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from projects.models import Project, ProjectMembership
from tasks.models import Task

User = get_user_model()


class Command(BaseCommand):
    help = "Seed the database with a demo admin, members, a project, and tasks."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin_demo",
            defaults={"email": "admin@example.com", "role": User.Role.ADMIN},
        )
        if created:
            admin.set_password("DemoPass123!")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created admin_demo / DemoPass123!"))

        member, created = User.objects.get_or_create(
            username="member_demo",
            defaults={"email": "member@example.com", "role": User.Role.MEMBER},
        )
        if created:
            member.set_password("DemoPass123!")
            member.save()
            self.stdout.write(self.style.SUCCESS("Created member_demo / DemoPass123!"))

        project, _ = Project.objects.get_or_create(
            name="Demo Website Revamp", defaults={"description": "Sample seeded project", "created_by": admin}
        )
        ProjectMembership.objects.get_or_create(project=project, user=admin, defaults={"role": "admin"})
        ProjectMembership.objects.get_or_create(project=project, user=member, defaults={"role": "member"})

        now = timezone.now()
        demo_tasks = [
            ("Design homepage mockup", Task.Status.DONE, now - timedelta(days=1)),
            ("Set up CI pipeline", Task.Status.IN_PROGRESS, now + timedelta(days=3)),
            ("Fix login bug", Task.Status.TODO, now - timedelta(days=2)),  # overdue
            ("Write API docs", Task.Status.TODO, now + timedelta(days=7)),
        ]
        for title, status_, due in demo_tasks:
            Task.objects.get_or_create(
                title=title,
                project=project,
                defaults={
                    "status": status_,
                    "assigned_to": member,
                    "created_by": admin,
                    "due_date": due,
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo data ready."))

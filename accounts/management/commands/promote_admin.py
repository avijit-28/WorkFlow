from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Promote an existing user to the 'admin' role (or demote back to 'member')."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument(
            "--demote",
            action="store_true",
            help="Set the user's role back to 'member' instead of promoting to 'admin'.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"No user found with username '{username}'.")

        user.role = User.Role.MEMBER if options["demote"] else User.Role.ADMIN
        user.save(update_fields=["role"])

        self.stdout.write(self.style.SUCCESS(f"{username} is now role='{user.role}'."))

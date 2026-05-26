import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create or update a Django superuser from environment variables."

    def handle(self, *args, **options):
        enabled = os.environ.get("DOCSEVA_CREATE_SUPERUSER", "False").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        if not enabled:
            self.stdout.write("Superuser bootstrap disabled.")
            return

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

        if not username or not password:
            raise CommandError(
                "Set DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD."
            )

        User = get_user_model()
        username_field = User.USERNAME_FIELD

        with transaction.atomic():
            user, created = User.objects.get_or_create(**{username_field: username})

            if hasattr(user, "email") and email:
                user.email = email

            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Superuser {username} {action}."))

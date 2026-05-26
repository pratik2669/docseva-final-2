from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.models import UserProfile


class Command(BaseCommand):
    help = "Promote an existing user to DocSeva Admin or Super Admin without relying on Django superuser."

    def add_arguments(self, parser):
        parser.add_argument("username_or_email")
        parser.add_argument("--role", choices=["admin", "superadmin"], default="admin")

    def handle(self, *args, **options):
        value = options["username_or_email"]
        role = options["role"]
        user = (
            User.objects.filter(username__iexact=value).first()
            or User.objects.filter(email__iexact=value).first()
        )
        if not user:
            raise CommandError(f"User not found: {value}")
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "name": user.get_full_name() or user.username,
                "email": user.email,
            },
        )
        profile.portal_role = role
        profile.is_portal_admin = True
        profile.save(update_fields=["portal_role", "is_portal_admin", "updated_at"])
        self.stdout.write(
            self.style.SUCCESS(f"{user.username} is now a DocSeva {role}.")
        )

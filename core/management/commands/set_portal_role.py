from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.models import UserProfile


class Command(BaseCommand):
    help = "Set DocSeva portal role: user, admin, or superadmin. This is separate from Django superuser."

    def add_arguments(self, parser):
        parser.add_argument("username_or_email")
        parser.add_argument("role", choices=["user", "admin", "superadmin"])

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
        profile.is_portal_admin = role in {"admin", "superadmin"}
        profile.save(update_fields=["portal_role", "is_portal_admin", "updated_at"])
        self.stdout.write(
            self.style.SUCCESS(f"{user.username} portal role set to {role}.")
        )

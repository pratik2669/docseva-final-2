from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailBackend(ModelBackend):
    """Authenticate with username or email without crashing on duplicate emails."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if not username or password is None:
            return None

        user = None
        if "@" in username:
            user = User.objects.filter(email__iexact=username).order_by("id").first()
        if user is None:
            user = User.objects.filter(username__iexact=username).order_by("id").first()

        if user is None:
            User().set_password(password)  # keep default password timing behavior
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

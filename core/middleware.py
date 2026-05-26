"""Custom middleware for DocSeva."""

from __future__ import annotations

from django.conf import settings


class PermissionsPolicyMiddleware:
    """Emit the Permissions-Policy header on every response.

    The value is controlled by ``settings.PERMISSIONS_POLICY``.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.policy = getattr(
            settings,
            "PERMISSIONS_POLICY",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )

    def __call__(self, request):
        response = self.get_response(request)
        response["Permissions-Policy"] = self.policy
        return response

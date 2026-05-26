from .forms import NewsletterForm
from .models import Notification, UserProfile


PUBLIC_PAGE_TITLES = {
    "landing": "Home",
    "about": "About",
    "pricing": "Pricing",
    "contact": "Contact",
    "faq": "FAQ",
    "resources": "Resources",
    "privacy": "Privacy Policy",
    "terms": "Terms of Service",
    "registration": "Create Account",
    "login": "Login",
    "password_reset": "Password Reset",
    "dashboard": "Dashboard",
    "document": "Documents",
    "vault": "Vault",
    "gov": "Gov Hub",
    "support": "Support",
    "security": "Security",
    "profile": "Profile",
    "settings": "Settings",
}


def _breadcrumbs(request):
    match = getattr(request, "resolver_match", None)
    if not match or match.url_name == "landing":
        return []
    current = PUBLIC_PAGE_TITLES.get(match.url_name, match.url_name.replace("_", " ").title())
    return [
        {"label": "Home", "url_name": "landing"},
        {"label": current, "url_name": None},
    ]


def docseva_context(request):
    """
    Global context injected into every template.
    Provides profile, role flags, unread notification count, breadcrumbs, and newsletter form.
    """
    base = {
        "breadcrumb_items": _breadcrumbs(request),
        "newsletter_form": NewsletterForm(initial={"source": "footer"}),
    }
    if not request.user.is_authenticated:
        base.update({
            "profile": None,
            "unread_notifications": 0,
            "is_portal_admin": False,
            "is_portal_superadmin": False,
            "portal_role": "guest",
        })
        return base
    profile = (
        UserProfile.objects.filter(user=request.user)
        .select_related("subscription")
        .first()
    )
    portal_role = profile.portal_role if profile else "user"
    is_portal_admin = bool(profile and profile.is_portal_staff)
    is_portal_superadmin = bool(profile and profile.is_portal_superadmin)
    base.update({
        "profile": profile,
        "unread_notifications": Notification.objects.filter(
            user=request.user, is_read=False
        ).count(),
        "is_portal_admin": is_portal_admin,
        "is_portal_superadmin": is_portal_superadmin,
        "portal_role": portal_role,
    })
    return base

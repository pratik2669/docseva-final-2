from __future__ import annotations

import base64
import json
import logging
import random
from io import BytesIO
from datetime import datetime, timedelta

import qrcode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Sum
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.http import require_GET, require_POST

try:
    from django_ratelimit.decorators import ratelimit
    from django_ratelimit.exceptions import Ratelimited

    HAS_RATELIMIT = True
except ImportError:  # graceful fallback if package not installed in dev
    HAS_RATELIMIT = False

    def ratelimit(*args, **kwargs):  # type: ignore[misc]
        def decorator(view):
            return view

        return decorator

    class Ratelimited(Exception):  # type: ignore[misc]
        pass


logger = logging.getLogger(__name__)

from .forms import (
    ABHALinkForm,
    AppointmentForm,
    DocumentRenewalForm,
    DocumentShareForm,
    DocumentUploadForm,
    EmergencyInfoForm,
    ProfileImageForm,
    RegistrationForm,
    SupportTicketForm,
    ContactMessageForm,
    NewsletterForm,
    UserProfileForm,
)
from .services.renewal import get_renewal_info
from .models import (
    ABHARecord,
    Appointment,
    ChatMessage,
    Document,
    Notification,
    SecurityLog,
    SubscriptionPlan,
    SupportTicket,
    UserProfile,
    NewsletterSubscriber,
    ContactMessage,
)


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def create_security_log(user, title, description="", status="success", request=None):
    return SecurityLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        title=title,
        description=description,
        status=status,
        ip_address=get_client_ip(request) if request is not None else "",
    )


def create_notification(user, title, message, notification_type="info"):
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
    )


def ensure_default_plan():
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name="free",
        defaults={
            "display_name": "Free",
            "price_monthly": 0,
            "storage_limit_mb": 5120,
            "features": ["Document vault", "Support tickets", "Security logs"],
        },
    )
    return plan


def ensure_profile(user):
    plan = ensure_default_plan()
    full_name = user.get_full_name().strip()
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "name": full_name or user.username,
            "email": user.email,
            "subscription": plan,
        },
    )
    changed = False
    if not profile.email and user.email:
        profile.email = user.email
        changed = True
    if profile.subscription is None:
        profile.subscription = plan
        changed = True
    if changed:
        profile.save()
    return profile


def page_queryset(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get("page"))


def get_portal_profile(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return UserProfile.objects.filter(user=user).first()


def is_admin_user(user):
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    profile = get_portal_profile(user)
    return bool(profile and profile.is_portal_staff)


def is_superadmin_user(user):
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    profile = get_portal_profile(user)
    return bool(profile and profile.is_portal_superadmin)


admin_required = user_passes_test(is_admin_user, login_url="login")
superadmin_required = user_passes_test(is_superadmin_user, login_url="admin_dashboard")


def role_home_url(user):
    if is_admin_user(user):
        return "admin_dashboard"
    return "dashboard"


def get_support_admin(exclude_user=None):
    qs = User.objects.filter(
        profile__portal_role__in=["admin", "superadmin"], is_active=True
    ).order_by("id")
    if exclude_user is not None and getattr(exclude_user, "is_authenticated", False):
        qs = qs.exclude(pk=exclude_user.pk)
    return qs.first()


def parse_bool_post(request, name):
    return request.POST.get(name) in {"on", "true", "1", "yes"}


def build_public_url(request, path):
    """Build scan/share URLs that work outside the browser that generated them.

    When PUBLIC_BASE_URL is set, QR codes and public share links use it. This
    fixes local LAN QR scanning: a phone cannot open a laptop-only localhost URL,
    but it can open http://<laptop-ip>:8000 when both devices are on the same Wi-Fi.
    """
    base_url = getattr(settings, "PUBLIC_BASE_URL", "")
    if base_url:
        return f"{base_url}{path}"
    return request.build_absolute_uri(path)


@require_GET
def health_check(request):
    return JsonResponse({"status": "ok", "service": "docseva"})


@require_GET
def robots_txt(request):
    sitemap_url = build_public_url(request, reverse("sitemap_xml"))
    body = (
        "User-agent: *\n"
        f"Disallow: /{settings.ADMIN_URL}\n"
        "Disallow: /portal/admin/\n"
        "Disallow: /profile/\n"
        "Disallow: /documents/\n"
        "Disallow: /api/\n"
        f"Sitemap: {sitemap_url}\n"
    )
    return HttpResponse(body, content_type="text/plain")


@require_GET
def site_manifest(request):
    return JsonResponse(
        {
            "name": "DocSeva",
            "short_name": "DocSeva",
            "description": "Secure document vault, renewal tracking, support, and emergency QR sharing.",
            "start_url": reverse("landing"),
            "display": "standalone",
            "background_color": "#f8fafc",
            "theme_color": "#2563eb",
            "icons": [
                {
                    "src": request.build_absolute_uri(static("core/img/logo.svg")),
                    "sizes": "128x128",
                    "type": "image/svg+xml",
                    "purpose": "any maskable",
                }
            ],
        }
    )


@require_GET
def sitemap_xml(request):
    public_names = [
        "landing",
        "about",
        "pricing",
        "contact",
        "faq",
        "resources",
        "privacy",
        "terms",
        "login",
        "registration",
        "password_reset",
    ]
    urls = []
    for name in public_names:
        try:
            urls.append(build_public_url(request, reverse(name)))
        except Exception:
            continue
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in urls:
        body.append(f"  <url><loc>{escape(url)}</loc></url>")
    body.append("</urlset>")
    return HttpResponse("\n".join(body), content_type="application/xml")


@require_GET
def security_txt(request):
    contact = getattr(settings, "SECURITY_CONTACT", "")
    lines = [
        "# DocSeva security contact",
        f"Contact: {contact}" if contact else "Contact: mailto:security@example.com",
        "Preferred-Languages: en, hi, mr",
        "Policy: /",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def landing_view(request):
    if request.user.is_authenticated:
        return redirect(role_home_url(request.user))
    return render(request, "core/landing_page.html")


def about_view(request):
    return render(request, "core/about.html")


def pricing_view(request):
    plans = [
        {"name": "Free", "price": "₹0", "description": "Basic document vault for personal use.", "features": ["Document vault", "Renewal reminders", "Emergency QR", "Support tickets"]},
        {"name": "Pro", "price": "₹199/mo", "description": "For families and power users who need more storage and priority help.", "features": ["Larger storage", "Priority support", "Advanced sharing", "Family-ready workflow"]},
        {"name": "Service Partner", "price": "Custom", "description": "For Seva Kendra style workflows and admin operations.", "features": ["Admin portal", "Security logs", "Role separation", "Deployment support"]},
    ]
    return render(request, "core/pricing.html", {"plans": plans})


def contact_view(request):
    form = ContactMessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ContactMessage.objects.create(
            name=form.cleaned_data["name"].strip(),
            email=form.cleaned_data["email"].strip().lower(),
            subject=form.cleaned_data["subject"].strip(),
            message=form.cleaned_data["message"].strip(),
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )
        messages.success(request, "Message received. Configure SMTP in production to send email alerts.")
        return redirect("contact")
    return render(request, "core/contact.html", {"form": form})


def faq_view(request):
    faqs = [
        ("Is DocSeva connected to government APIs?", "The included GOV Hub flows run in mock/demo mode unless GOV_API_MODE and real government integrations are configured."),
        ("Can users share a document by QR or link?", "Yes. Sharing is token-based, can expire, and download permission is separately controlled by the owner."),
        ("Can I deploy it on Render?", "Yes. The project includes render.yaml, Procfile, Dockerfile, PostgreSQL-ready settings, and collectstatic support."),
        ("Do I need PostgreSQL?", "Use PostgreSQL for production. SQLite is only acceptable for local development."),
        ("Does password reset work immediately?", "Locally it prints to console. Production needs real SMTP variables."),
    ]
    return render(request, "core/faq.html", {"faqs": faqs})


def resources_view(request):
    resources = [
        {"title": "Production launch checklist", "summary": "Security, database, static files, email, monitoring, backups, and deployment tasks before going live."},
        {"title": "Document renewal workflow", "summary": "How expiry dates, renewal notes, and reminders reduce missed deadlines."},
        {"title": "Emergency QR setup", "summary": "How to decide what emergency information should be public after scanning."},
    ]
    return render(request, "core/resources.html", {"resources": resources})


@ratelimit(key="ip", rate="8/h", method="POST", block=True)
@require_POST
def newsletter_subscribe_view(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        NewsletterSubscriber.objects.update_or_create(
            email=email,
            defaults={
                "source": form.cleaned_data.get("source") or "footer",
                "consent": form.cleaned_data["consent"],
                "is_active": True,
            },
        )
        messages.success(request, "Newsletter signup saved.")
    else:
        messages.error(request, "Enter a valid email and accept newsletter consent.")
    return redirect(request.META.get("HTTP_REFERER") or "landing")


def privacy_view(request):
    return render(request, "core/privacy.html")


def terms_view(request):
    return render(request, "core/terms.html")


@ratelimit(key="ip", rate="10/h", method="POST", block=True)
def registration_view(request):
    if request.user.is_authenticated:
        return redirect(role_home_url(request.user))
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "name": user.get_full_name() or user.username,
                "email": user.email,
                "subscription": ensure_default_plan(),
            },
        )
        create_security_log(
            user, "Account Created", "User registered successfully.", "success", request
        )
        create_notification(
            user, "Welcome to DocSeva", "Your account is ready.", "success"
        )
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Registration successful.")
        return redirect("dashboard")
    return render(request, "core/registration.html", {"form": form})


@ratelimit(key="ip", rate="20/h", method="POST", block=True)
def login_view(request):
    if request.user.is_authenticated:
        return redirect(role_home_url(request.user))
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            ensure_profile(user)
            create_security_log(
                user, "Login Successful", "User logged in.", "success", request
            )
            logger.info(
                "login.success",
                extra={"user": user.username, "ip": get_client_ip(request)},
            )
            messages.success(request, "Logged in successfully.")
            return redirect(role_home_url(user))
        failed_user = (
            User.objects.filter(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
            .order_by("id")
            .first()
        )
        create_security_log(
            failed_user, "Login Failed", "Invalid login attempt.", "failed", request
        )
        logger.warning(
            "login.failed",
            extra={"attempted_username": username, "ip": get_client_ip(request)},
        )
        messages.error(request, "Invalid username/email or password.")
    return render(request, "core/login.html")


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        create_security_log(
            request.user, "Logout", "User logged out.", "success", request
        )
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("landing")


@login_required
def dashboard_view(request):
    if is_admin_user(request.user):
        return redirect("admin_dashboard")
    user = request.user
    profile = ensure_profile(user)
    documents = Document.objects.filter(user=user)
    tickets = SupportTicket.objects.filter(user=user)
    recent_logs = SecurityLog.objects.filter(user=user)[:5]
    expiring_documents = documents.filter(
        expiry_date__isnull=False,
        expiry_date__gte=timezone.localdate(),
        expiry_date__lte=timezone.localdate() + timedelta(days=45),
    )[:5]
    expired_documents = documents.filter(expiry_date__lt=timezone.localdate())[:5]
    context = {
        "profile": profile,
        "documents_count": documents.count(),
        "recent_documents": documents[:5],
        "tickets_count": tickets.count(),
        "open_tickets": tickets.exclude(status="closed").count(),
        "recent_tickets": tickets[:5],
        "security_logs": recent_logs,
        "storage_used_mb": profile.storage_used_mb,
        "storage_used_percent": profile.storage_used_percent,
        "appointments_count": Appointment.objects.filter(user=user).count(),
        "notifications_count": Notification.objects.filter(
            user=user, is_read=False
        ).count(),
        "expiring_documents": expiring_documents,
        "expired_documents": expired_documents,
    }
    return render(request, "core/dashboard.html", context)


@login_required
def document_view(request):
    user = request.user
    ensure_profile(user)
    documents = Document.objects.filter(user=user)
    category = request.GET.get("category", "").strip()
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if category:
        documents = documents.filter(category=category)
    if query:
        documents = documents.filter(
            Q(title__icontains=query)
            | Q(source__icontains=query)
            | Q(shared_with__icontains=query)
        )
    if status == "expiring":
        documents = documents.filter(
            expiry_date__isnull=False,
            expiry_date__gte=timezone.localdate(),
            expiry_date__lte=timezone.localdate() + timedelta(days=45),
        )
    elif status == "expired":
        documents = documents.filter(expiry_date__lt=timezone.localdate())
    return render(
        request,
        "core/document_explorer.html",
        {
            "documents_page": page_queryset(request, documents, 10),
            "documents": documents,
            "form": DocumentUploadForm(),
            "category": category,
            "query": query,
            "status": status,
            "categories": Document.CATEGORY_CHOICES,
        },
    )


@login_required
@require_POST
def upload_view(request):
    user = request.user
    profile = ensure_profile(user)
    form = DocumentUploadForm(request.POST, request.FILES)
    if form.is_valid():
        uploaded_file = form.cleaned_data["file"]
        limit_bytes = (
            (profile.subscription.storage_limit_mb if profile.subscription else 5120)
            * 1024
            * 1024
        )
        current_bytes = sum(doc.file_size for doc in user.documents.all())
        if current_bytes + uploaded_file.size > limit_bytes:
            messages.error(request, "Upload rejected: storage quota exceeded.")
            return redirect("document")
        document = form.save(commit=False)
        document.user = user
        document.save()
        create_security_log(
            user, "Document Uploaded", f"Uploaded {document.title}", "success", request
        )
        create_notification(
            user, "Document Uploaded", f"{document.title} was uploaded.", "success"
        )
        messages.success(request, "Document uploaded successfully.")
    else:
        for field, field_errors in form.errors.items():
            for error in field_errors:
                messages.error(request, f"{field}: {error}")
    return redirect("document")


@login_required
def document_detail_view(request, pk):
    document = get_object_or_404(Document, pk=pk, user=request.user)
    return render(
        request,
        "core/document_detail.html",
        {
            "document": document,
            "share_form": DocumentShareForm(
                initial={
                    "shared_with": document.shared_with,
                    "share_enabled": document.share_enabled,
                    "share_download_enabled": document.share_download_enabled,
                    "share_message": document.share_message,
                }
            ),
            "share_url": build_public_url(
                request, reverse("public_document_share", args=[document.share_token])
            ),
            "renewal_info": get_renewal_info(document.category),
            "renewal_map_url": document.renewal_maps_url(),
        },
    )


@login_required
@require_POST
def document_share_view(request, pk):
    document = get_object_or_404(Document, pk=pk, user=request.user)
    form = DocumentShareForm(request.POST)
    if form.is_valid():
        document.shared_with = form.cleaned_data["shared_with"]
        document.share_enabled = form.cleaned_data["share_enabled"]
        document.share_download_enabled = (
            form.cleaned_data["share_download_enabled"]
            if document.share_enabled
            else False
        )
        document.share_message = form.cleaned_data.get("share_message", "")
        days = int(form.cleaned_data.get("share_expires_days") or 30)
        document.share_expires_at = (
            None if days == 0 else timezone.now() + timedelta(days=days)
        )
        document.save(
            update_fields=[
                "shared_with",
                "share_enabled",
                "share_download_enabled",
                "share_message",
                "share_expires_at",
            ]
        )
        create_security_log(
            request.user,
            "Document Sharing Updated",
            f"Updated sharing for {document.title}",
            "success",
            request,
        )
        if document.share_enabled:
            messages.success(
                request, "Secure share link is active. Copy it from this page."
            )
        else:
            messages.success(request, "Sharing disabled and metadata updated.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect("document_detail", pk=document.pk)


@login_required
def document_download_view(request, pk):
    document = get_object_or_404(Document, pk=pk, user=request.user)
    if not document.file:
        return HttpResponseForbidden("File not found.")
    create_security_log(
        request.user,
        "Document Downloaded",
        f"Downloaded {document.title}",
        "success",
        request,
    )
    response = FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.file.name.split("/")[-1],
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@require_POST
def document_delete_view(request, pk):
    document = get_object_or_404(Document, pk=pk, user=request.user)
    title = document.title
    if document.file:
        document.file.delete(save=False)
    document.delete()
    create_security_log(
        request.user, "Document Deleted", f"Deleted {title}", "warning", request
    )
    create_notification(
        request.user, "Document Deleted", f"{title} was deleted.", "warning"
    )
    messages.success(request, "Document deleted.")
    return redirect("document")


@login_required
def document_renewal_view(request, pk):
    document = get_object_or_404(Document, pk=pk, user=request.user)
    form = DocumentRenewalForm(instance=document)
    if request.method == "POST":
        form = DocumentRenewalForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            create_security_log(
                request.user,
                "Renewal Tracking Updated",
                f"Updated renewal status for {document.title}.",
                "success",
                request,
            )
            create_notification(
                request.user,
                "Renewal tracking updated",
                f"{document.title} renewal details were updated.",
                "info",
            )
            messages.success(request, "Renewal details saved.")
            return redirect("document_renewal", pk=document.pk)
    renewal_info = get_renewal_info(document.category)
    return render(
        request,
        "core/document_renewal.html",
        {
            "document": document,
            "form": form,
            "renewal_info": renewal_info,
            "renewal_map_url": document.renewal_maps_url(),
        },
    )


@login_required
def sharing_view(request):
    documents = Document.objects.filter(user=request.user).exclude(shared_with="")
    return render(
        request,
        "core/document_explorer.html",
        {
            "documents_page": page_queryset(request, documents, 10),
            "documents": documents,
            "shared_only": True,
            "form": DocumentUploadForm(),
            "categories": Document.CATEGORY_CHOICES,
        },
    )


@login_required
def profile_view(request):
    profile = ensure_profile(request.user)
    profile_form = UserProfileForm(instance=profile, user=request.user)
    image_form = ProfileImageForm(instance=profile)
    emergency_form = EmergencyInfoForm(instance=profile)

    if request.method == "POST":
        action = request.POST.get("action", "profile")
        if action == "image":
            image_form = ProfileImageForm(request.POST, request.FILES, instance=profile)
            if image_form.is_valid():
                image_form.save()
                create_security_log(
                    request.user,
                    "Profile Image Updated",
                    "User updated profile image.",
                    "success",
                    request,
                )
                messages.success(request, "Profile image updated.")
                return redirect("profile")
        elif action == "emergency":
            emergency_form = EmergencyInfoForm(request.POST, instance=profile)
            if emergency_form.is_valid():
                emergency_form.save()
                create_security_log(
                    request.user,
                    "Emergency QR Updated",
                    "User updated emergency QR medical information.",
                    "success",
                    request,
                )
                messages.success(request, "Emergency QR medical information updated.")
                return redirect("profile")
        else:
            profile_form = UserProfileForm(
                request.POST, instance=profile, user=request.user
            )
            if profile_form.is_valid():
                profile_form.save()
                create_security_log(
                    request.user,
                    "Profile Updated",
                    "User updated profile details.",
                    "success",
                    request,
                )
                messages.success(request, "Profile updated.")
                return redirect("profile")
    emergency_url = build_public_url(request, profile.emergency_public_path())
    return render(
        request,
        "core/user_profile.html",
        {
            "profile": profile,
            "profile_form": profile_form,
            "image_form": image_form,
            "emergency_form": emergency_form,
            "emergency_url": emergency_url,
        },
    )


@login_required
def emergency_qr_view(request):
    profile = ensure_profile(request.user)
    emergency_url = build_public_url(request, profile.emergency_public_path())
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(emergency_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    qr_data_uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode(
        "ascii"
    )
    return render(
        request,
        "core/emergency_qr.html",
        {
            "profile": profile,
            "qr_data_uri": qr_data_uri,
            "emergency_url": emergency_url,
        },
    )


@ratelimit(key="ip", rate="120/h", method="GET", block=True)
def emergency_public_view(request, token):
    profile = get_object_or_404(
        UserProfile.objects.select_related("user"),
        emergency_token=token,
        emergency_share_enabled=True,
    )
    if not profile.has_emergency_info:
        return render(
            request, "core/emergency_public.html", {"profile": profile, "empty": True}
        )
    return render(
        request, "core/emergency_public.html", {"profile": profile, "empty": False}
    )


@login_required
def gov_view(request):
    user = request.user
    profile = ensure_profile(user)
    abha_form = ABHALinkForm()
    appointment_form = AppointmentForm()

    if request.method == "POST" and "abha_id" in request.POST:
        abha_form = ABHALinkForm(request.POST)
        if abha_form.is_valid():
            profile.abha_id = abha_form.cleaned_data["abha_id"]
            profile.save(update_fields=["abha_id"])
            create_notification(user, "ABHA Linked", "ABHA ID saved.", "success")
            create_security_log(
                user, "ABHA ID Saved", "User saved ABHA ID.", "success", request
            )
            messages.success(request, "ABHA ID saved.")
            return redirect("gov")
    elif request.method == "POST" and "doctor_name" in request.POST:
        appointment_form = AppointmentForm(request.POST)
        if appointment_form.is_valid():
            appointment = appointment_form.save(commit=False)
            appointment.user = user
            appointment.save()
            create_notification(
                user,
                "Appointment Booked",
                f"Appointment with {appointment.doctor_name} created.",
                "success",
            )
            create_security_log(
                user,
                "Appointment Booked",
                f"Appointment with {appointment.doctor_name} created.",
                "success",
                request,
            )
            messages.success(request, "Appointment booked.")
            return redirect("gov")

    return render(
        request,
        "core/gov.html",
        {
            "profile": profile,
            "abha_form": abha_form,
            "appointment_form": appointment_form,
            "appointments": Appointment.objects.filter(user=user).order_by("-datetime")[
                :10
            ],
            "abha_records": ABHARecord.objects.filter(user=user)[:10],
            "gov_api_mode": settings.GOV_API_MODE,
        },
    )


@login_required
@require_POST
@ratelimit(key="user_or_ip", rate="20/h", method="POST", block=True)
def abha_sync_view(request):
    profile = ensure_profile(request.user)
    if not profile.abha_id:
        return JsonResponse(
            {"success": False, "error": "Link an ABHA ID first."}, status=400
        )
    if settings.GOV_API_MODE != "mock":
        return JsonResponse(
            {"success": False, "error": "Real ABHA integration is not configured."},
            status=501,
        )
    record_types = ["allergy", "medication", "condition", "immunization", "lab"]
    created = []
    for record_type in random.sample(record_types, k=2):
        record = ABHARecord.objects.create(
            user=request.user,
            abha_id=profile.abha_id,
            record_type=record_type,
            data={
                "source": "Mock demo data",
                "status": "Demo only",
                "synced": timezone.now().isoformat(),
            },
        )
        created.append(record.record_type)
    create_security_log(
        request.user,
        "Mock ABHA Sync",
        f"Created {len(created)} demo records.",
        "success",
        request,
    )
    return JsonResponse(
        {
            "success": True,
            "demo": True,
            "records_synced": len(created),
            "types": created,
        }
    )


@login_required
@require_POST
@ratelimit(key="user_or_ip", rate="20/h", method="POST", block=True)
def ayushman_eligibility_view(request):
    if settings.GOV_API_MODE != "mock":
        return JsonResponse(
            {"success": False, "error": "Real PM-JAY integration is not configured."},
            status=501,
        )
    create_security_log(
        request.user,
        "Mock Ayushman Check",
        "User ran demo eligibility check.",
        "success",
        request,
    )
    return JsonResponse(
        {
            "success": True,
            "demo": True,
            "eligible": False,
            "pmjay_id": None,
            "coverage_amount": "Demo only",
            "message": "Mock result. Connect official APIs before real use.",
        }
    )


@login_required
def support_view(request):
    user = request.user
    ticket_form = SupportTicketForm(request.POST or None)
    if request.method == "POST" and ticket_form.is_valid():
        ticket = ticket_form.save(commit=False)
        ticket.user = user
        ticket.save()
        create_notification(
            user, "Support Ticket Created", f"Ticket #{ticket.id} opened.", "success"
        )
        create_security_log(
            user,
            "Support Ticket Created",
            f"Ticket #{ticket.id} opened.",
            "success",
            request,
        )
        messages.success(request, f"Ticket #{ticket.id} created.")
        return redirect("support")
    messages_qs = ChatMessage.objects.filter(
        Q(sender=user) | Q(receiver=user)
    ).order_by("timestamp")[:50]
    return render(
        request,
        "core/support_center.html",
        {
            "tickets": SupportTicket.objects.filter(user=user),
            "ticket_form": ticket_form,
            "chat_messages": messages_qs,
        },
    )


@login_required
@require_POST
@ratelimit(key="user_or_ip", rate="60/h", method="POST", block=True)
def chat_send_view(request):
    message = request.POST.get("message", "").strip()
    if not message:
        return JsonResponse(
            {"success": False, "error": "Message cannot be empty."}, status=400
        )
    msg = ChatMessage.objects.create(
        sender=request.user,
        receiver=get_support_admin(exclude_user=request.user),
        message=message[:1000],
    )
    create_security_log(
        request.user,
        "Support Chat Message",
        "User sent a support chat message.",
        "success",
        request,
    )
    return JsonResponse(
        {
            "success": True,
            "id": msg.id,
            "sender": msg.sender.username,
            "message": msg.message,
            "timestamp": msg.timestamp.strftime("%b %d, %H:%M"),
            "is_me": True,
        }
    )


@login_required
def chat_poll_view(request):
    try:
        last_id = int(request.GET.get("last_id", 0))
    except ValueError:
        last_id = 0
    messages_qs = (
        ChatMessage.objects.filter(Q(sender=request.user) | Q(receiver=request.user))
        .filter(id__gt=last_id)
        .order_by("timestamp")
    )
    return JsonResponse(
        {
            "messages": [
                {
                    "id": msg.id,
                    "sender": msg.sender.username,
                    "message": msg.message,
                    "timestamp": msg.timestamp.strftime("%b %d, %H:%M"),
                    "is_me": msg.sender_id == request.user.id,
                }
                for msg in messages_qs
            ]
        }
    )


@login_required
def security_view(request):
    logs_qs = SecurityLog.objects.filter(user=request.user)
    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        logs_qs = logs_qs.filter(status=status_filter)
    return render(
        request,
        "core/security_log.html",
        {
            "logs_page": page_queryset(request, logs_qs, 20),
            "logs": logs_qs[:100],
            "status_filter": status_filter,
            "total_logs": SecurityLog.objects.filter(user=request.user).count(),
            "success_logs": SecurityLog.objects.filter(
                user=request.user, status="success"
            ).count(),
            "failed_logs": SecurityLog.objects.filter(
                user=request.user, status="failed"
            ).count(),
            "warning_logs": SecurityLog.objects.filter(
                user=request.user, status="warning"
            ).count(),
        },
    )


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user)[:20]
    return JsonResponse(
        {
            "notifications": [
                {
                    "id": item.id,
                    "title": item.title,
                    "message": item.message,
                    "type": item.notification_type,
                    "is_read": item.is_read,
                    "created_at": item.created_at.strftime("%b %d, %H:%M"),
                }
                for item in notifications
            ],
            "unread_count": Notification.objects.filter(
                user=request.user, is_read=False
            ).count(),
        }
    )


@login_required
@require_POST
def notification_mark_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return JsonResponse({"success": True})


@login_required
@require_POST
def notifications_mark_all_read_view(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"success": True})


@admin_required
def admin_dashboard_view(request):
    users_qs = User.objects.select_related("profile").order_by("-date_joined")
    documents_qs = Document.objects.select_related("user").order_by("-created_at")
    tickets_qs = SupportTicket.objects.select_related("user").order_by("-created_at")
    logs_qs = SecurityLog.objects.select_related("user").order_by("-timestamp")
    context = {
        "total_users": users_qs.count(),
        "active_users": users_qs.filter(is_active=True).count(),
        "portal_admins": users_qs.filter(profile__portal_role="admin").count(),
        "portal_superadmins": users_qs.filter(
            profile__portal_role="superadmin"
        ).count(),
        "normal_users": users_qs.filter(profile__portal_role="user").count(),
        "staff_users": users_qs.filter(is_staff=True).count(),
        "total_documents": documents_qs.count(),
        "storage_used_mb": round(
            (documents_qs.aggregate(total=Sum("file_size"))["total"] or 0)
            / (1024 * 1024),
            2,
        ),
        "total_tickets": tickets_qs.count(),
        "open_tickets": tickets_qs.exclude(status="closed").count(),
        "total_appointments": Appointment.objects.count(),
        "expiring_documents": documents_qs.filter(
            expiry_date__isnull=False,
            expiry_date__gte=timezone.localdate(),
            expiry_date__lte=timezone.localdate() + timedelta(days=45),
        )[:8],
        "recent_users": users_qs[:8],
        "recent_documents": documents_qs[:8],
        "recent_tickets": tickets_qs[:8],
        "recent_logs": logs_qs[:8],
    }
    return render(request, "core/admin/dashboard.html", context)


@admin_required
def admin_user_list_view(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    users = User.objects.select_related("profile").order_by("-date_joined")
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(profile__name__icontains=query)
        )
    if role == "admin":
        users = users.filter(profile__portal_role="admin")
    elif role == "superadmin":
        users = users.filter(profile__portal_role="superadmin")
    elif role == "technical_superuser":
        users = users.filter(is_superuser=True)
    elif role == "user":
        users = users.filter(profile__portal_role="user")
    elif role == "inactive":
        users = users.filter(is_active=False)
    return render(
        request,
        "core/admin/users.html",
        {"users_page": page_queryset(request, users, 20), "query": query, "role": role},
    )


@admin_required
def admin_user_detail_view(request, pk):
    target = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    profile = ensure_profile(target)
    current_profile = ensure_profile(request.user)
    current_is_superadmin = current_profile.is_portal_superadmin

    if request.method == "POST":
        if target == request.user and not parse_bool_post(request, "is_active"):
            messages.error(request, "You cannot deactivate your own account.")
            return redirect("admin_user_detail", pk=target.pk)

        target.first_name = request.POST.get("first_name", "").strip()
        target.last_name = request.POST.get("last_name", "").strip()
        target.email = request.POST.get("email", "").strip().lower()
        target.is_active = parse_bool_post(request, "is_active")
        target.save(update_fields=["first_name", "last_name", "email", "is_active"])

        profile.name = request.POST.get("name", "").strip()
        profile.phone = request.POST.get("phone", "").strip()
        profile.location = request.POST.get("location", "").strip()
        profile.department = request.POST.get("department", "").strip()
        profile.email = target.email

        requested_role = request.POST.get("portal_role", profile.portal_role)
        allowed_roles = {"user", "admin", "superadmin"}
        if requested_role not in allowed_roles:
            requested_role = profile.portal_role

        if current_is_superadmin:
            if target == request.user and requested_role != "superadmin":
                other_superadmin_exists = (
                    UserProfile.objects.filter(
                        portal_role="superadmin", user__is_active=True
                    )
                    .exclude(user=target)
                    .exists()
                )
                if not other_superadmin_exists:
                    messages.error(
                        request, "At least one active DocSeva Super Admin is required."
                    )
                    return redirect("admin_user_detail", pk=target.pk)
            profile.portal_role = requested_role
            profile.is_portal_admin = requested_role in {"admin", "superadmin"}
        else:
            # Normal DocSeva Admins can edit user details, but cannot change roles.
            if (
                request.POST.get("portal_role")
                and request.POST.get("portal_role") != profile.portal_role
            ):
                messages.warning(
                    request, "Only a DocSeva Super Admin can change portal roles."
                )

        profile.save(
            update_fields=[
                "name",
                "phone",
                "location",
                "department",
                "email",
                "portal_role",
                "is_portal_admin",
                "updated_at",
            ]
        )
        create_security_log(
            request.user,
            "Admin Updated User",
            f"Updated account {target.username}.",
            "warning",
            request,
        )
        messages.success(request, "User account updated.")
        return redirect("admin_user_detail", pk=target.pk)

    context = {
        "target": target,
        "profile": profile,
        "current_is_superadmin": current_is_superadmin,
        "role_choices": UserProfile.PORTAL_ROLE_CHOICES,
        "documents": Document.objects.filter(user=target)[:10],
        "tickets": SupportTicket.objects.filter(user=target)[:10],
        "logs": SecurityLog.objects.filter(user=target)[:10],
    }
    return render(request, "core/admin/user_detail.html", context)


@admin_required
def admin_document_list_view(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    documents = Document.objects.select_related("user").order_by("-created_at")
    if query:
        documents = documents.filter(
            Q(title__icontains=query)
            | Q(source__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
        )
    if category:
        documents = documents.filter(category=category)
    return render(
        request,
        "core/admin/documents.html",
        {
            "documents_page": page_queryset(request, documents, 20),
            "query": query,
            "category": category,
            "categories": Document.CATEGORY_CHOICES,
        },
    )


@admin_required
def admin_document_download_view(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if not document.file:
        return HttpResponseForbidden("File not found.")
    create_security_log(
        request.user,
        "Admin Downloaded Document",
        f"Downloaded {document.title} from {document.user.username}.",
        "warning",
        request,
    )
    response = FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.file.name.split("/")[-1],
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@admin_required
@require_POST
def admin_document_delete_view(request, pk):
    document = get_object_or_404(Document, pk=pk)
    title = document.title
    owner = document.user
    if document.file:
        document.file.delete(save=False)
    document.delete()
    create_notification(
        owner,
        "Document Removed by Admin",
        f"{title} was removed by support/admin.",
        "warning",
    )
    create_security_log(
        request.user,
        "Admin Deleted Document",
        f"Deleted {title} from {owner.username}.",
        "warning",
        request,
    )
    messages.success(request, "Document deleted.")
    return redirect("admin_documents")


@admin_required
def admin_ticket_list_view(request):
    status_filter = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()
    tickets = SupportTicket.objects.select_related("user").order_by("-created_at")
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if query:
        tickets = tickets.filter(
            Q(subject__icontains=query)
            | Q(message__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
        )
    return render(
        request,
        "core/admin/tickets.html",
        {
            "tickets_page": page_queryset(request, tickets, 20),
            "status_filter": status_filter,
            "query": query,
            "statuses": SupportTicket.STATUS_CHOICES,
        },
    )


@admin_required
def admin_ticket_detail_view(request, pk):
    ticket = get_object_or_404(SupportTicket.objects.select_related("user"), pk=pk)
    if request.method == "POST":
        action = request.POST.get("action", "update")
        if action == "reply":
            message = request.POST.get("message", "").strip()
            if message:
                ChatMessage.objects.create(
                    sender=request.user, receiver=ticket.user, message=message[:1000]
                )
                create_notification(
                    ticket.user, "New support chat reply", message[:160], "info"
                )
                create_security_log(
                    request.user,
                    "Admin Chat Reply",
                    f"Replied to {ticket.user.username}.",
                    "success",
                    request,
                )
                messages.success(request, "Chat reply sent.")
            else:
                messages.error(request, "Reply message cannot be empty.")
        else:
            ticket.status = request.POST.get("status", ticket.status)
            ticket.admin_response = request.POST.get("admin_response", "").strip()
            ticket.save(update_fields=["status", "admin_response", "updated_at"])
            create_notification(
                ticket.user,
                "Support Ticket Updated",
                f"Ticket #{ticket.id} is now {ticket.get_status_display()}.",
                "info",
            )
            create_security_log(
                request.user,
                "Admin Updated Ticket",
                f"Updated ticket #{ticket.id}.",
                "success",
                request,
            )
            messages.success(request, "Ticket updated.")
        return redirect("admin_ticket_detail", pk=ticket.pk)
    chats = ChatMessage.objects.filter(
        Q(sender=ticket.user) | Q(receiver=ticket.user)
    ).order_by("timestamp")[:100]
    return render(
        request,
        "core/admin/ticket_detail.html",
        {"ticket": ticket, "chats": chats, "statuses": SupportTicket.STATUS_CHOICES},
    )


@admin_required
def admin_security_log_list_view(request):
    status_filter = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()
    logs = SecurityLog.objects.select_related("user").order_by("-timestamp")
    if status_filter:
        logs = logs.filter(status=status_filter)
    if query:
        logs = logs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(user__username__icontains=query)
            | Q(ip_address__icontains=query)
        )
    return render(
        request,
        "core/admin/security_logs.html",
        {
            "logs_page": page_queryset(request, logs, 30),
            "status_filter": status_filter,
            "query": query,
            "statuses": SecurityLog.STATUS_CHOICES,
        },
    )


@admin_required
def admin_appointment_list_view(request):
    query = request.GET.get("q", "").strip()
    appointments = Appointment.objects.select_related("user").order_by("-datetime")
    if query:
        appointments = appointments.filter(
            Q(doctor_name__icontains=query)
            | Q(department__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
        )
    return render(
        request,
        "core/admin/appointments.html",
        {"appointments_page": page_queryset(request, appointments, 20), "query": query},
    )


@login_required
def search_view(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return redirect("document")
    documents = Document.objects.filter(user=request.user).filter(
        Q(title__icontains=query)
        | Q(source__icontains=query)
        | Q(category__icontains=query)
        | Q(shared_with__icontains=query)
    )
    tickets = SupportTicket.objects.filter(user=request.user).filter(
        Q(subject__icontains=query) | Q(message__icontains=query)
    )
    appointments = Appointment.objects.filter(user=request.user).filter(
        Q(doctor_name__icontains=query) | Q(department__icontains=query)
    )
    return render(
        request,
        "core/search_results.html",
        {
            "query": query,
            "documents": documents,
            "tickets": tickets,
            "appointments": appointments,
        },
    )


@ratelimit(key="ip", rate="120/h", method="GET", block=True)
def public_document_share_view(request, token):
    document = get_object_or_404(
        Document.objects.select_related("user", "user__profile"), share_token=token
    )
    if not document.public_share_is_active:
        raise Http404("This document share link is inactive or expired.")
    Document.objects.filter(pk=document.pk).update(
        share_views=models.F("share_views") + 1
    )
    document.refresh_from_db(fields=["share_views"])
    create_security_log(
        document.user,
        "Document Share Viewed",
        f"Public share opened for {document.title}.",
        "success",
        request,
    )
    return render(request, "core/document_public_share.html", {"document": document})


@ratelimit(key="ip", rate="30/h", method="GET", block=True)
def public_document_download_view(request, token):
    document = get_object_or_404(Document, share_token=token)
    if not document.public_share_is_active or not document.share_download_enabled:
        raise Http404("Download is not available for this share link.")
    create_security_log(
        document.user,
        "Document Shared Download",
        f"Shared download for {document.title}.",
        "warning",
        request,
    )
    response = FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.file.name.split("/")[-1],
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def settings_view(request):
    return redirect("profile")


# ---------------------------------------------------------------------------
# Custom error handlers
# ---------------------------------------------------------------------------


def handler400(request, exception=None):
    return render(request, "core/errors/400.html", status=400)


def handler403(request, exception=None):
    return render(request, "core/errors/403.html", status=403)


def handler404(request, exception=None):
    return render(request, "core/errors/404.html", status=404)


def handler429(request, exception=None):
    """Rate limit exceeded."""
    return render(request, "core/errors/429.html", status=429)


def handler500(request):
    logger.exception("server.error.500", extra={"path": request.path})
    return render(request, "core/errors/500.html", status=500)

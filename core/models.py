import uuid
from urllib.parse import quote_plus

from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


class SubscriptionPlan(models.Model):
    PLAN_CHOICES = [
        ("free", "Free"),
        ("pro", "Pro"),
        ("elite", "Elite Concierge"),
    ]
    name = models.CharField(max_length=50, choices=PLAN_CHOICES, default="free")
    display_name = models.CharField(max_length=100)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    storage_limit_mb = models.PositiveIntegerField(default=5120)  # 5GB default
    features = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name


class UserProfile(models.Model):
    PORTAL_ROLE_USER = "user"
    PORTAL_ROLE_ADMIN = "admin"
    PORTAL_ROLE_SUPERADMIN = "superadmin"
    PORTAL_ROLE_CHOICES = [
        (PORTAL_ROLE_USER, "User"),
        (PORTAL_ROLE_ADMIN, "Admin"),
        (PORTAL_ROLE_SUPERADMIN, "Super Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=200, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    license_expiry = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    image = models.ImageField(upload_to="profiles/", blank=True, null=True)
    abha_id = models.CharField(max_length=50, blank=True)
    is_2fa_enabled = models.BooleanField(default=False)

    # Custom DocSeva portal role. This is separate from Django staff/superuser.
    portal_role = models.CharField(
        max_length=20, choices=PORTAL_ROLE_CHOICES, default=PORTAL_ROLE_USER
    )
    # Backward-compatible flag kept for older migrations/templates.
    is_portal_admin = models.BooleanField(default=False)

    # Emergency QR medical profile. Only these fields are exposed when enabled.
    emergency_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    emergency_share_enabled = models.BooleanField(default=False)
    blood_group = models.CharField(max_length=10, blank=True)
    allergies = models.TextField(blank=True)
    chronic_conditions = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    primary_doctor = models.CharField(max_length=120, blank=True)
    emergency_notes = models.TextField(blank=True)
    subscription = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscribers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or self.user.username

    @property
    def display_name(self):
        return self.name or (
            f"Dr. {self.user.first_name}"
            if self.user.first_name
            else self.user.username
        )

    @property
    def is_portal_user(self):
        return self.portal_role == self.PORTAL_ROLE_USER

    @property
    def is_portal_staff(self):
        return (
            self.portal_role in {self.PORTAL_ROLE_ADMIN, self.PORTAL_ROLE_SUPERADMIN}
            or self.is_portal_admin
        )

    @property
    def is_portal_superadmin(self):
        return self.portal_role == self.PORTAL_ROLE_SUPERADMIN

    @property
    def role_label(self):
        return dict(self.PORTAL_ROLE_CHOICES).get(self.portal_role, "User")

    def save(self, *args, **kwargs):
        self.is_portal_admin = self.portal_role in {
            self.PORTAL_ROLE_ADMIN,
            self.PORTAL_ROLE_SUPERADMIN,
        }
        super().save(*args, **kwargs)

    @property
    def storage_used_mb(self):
        total = sum(doc.file_size for doc in self.user.documents.all())
        return round(total / (1024 * 1024), 2)

    @property
    def storage_used_percent(self):
        limit = self.subscription.storage_limit_mb if self.subscription else 5120
        if limit == 0:
            return 0
        return min(100, round((self.storage_used_mb / limit) * 100, 1))

    def emergency_public_path(self):
        return reverse("emergency_public", args=[self.emergency_token])

    @property
    def has_emergency_info(self):
        return any(
            [
                self.blood_group,
                self.allergies,
                self.chronic_conditions,
                self.current_medications,
                self.emergency_contact,
                self.primary_doctor,
                self.emergency_notes,
            ]
        )


class Document(models.Model):
    CATEGORY_CHOICES = [
        ("lab", "Laboratory Report"),
        ("imaging", "Imaging & Scans"),
        ("prescription", "Prescription"),
        ("id", "ID Verification"),
        ("other", "Other"),
    ]
    RENEWAL_STATUS_CHOICES = [
        ("not_required", "Not required"),
        ("needs_review", "Needs review"),
        ("renewal_started", "Renewal started"),
        ("renewed", "Renewed"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="docs/")
    file_size = models.PositiveBigIntegerField(default=0)
    file_type = models.CharField(max_length=100, blank=True)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="other"
    )
    source = models.CharField(max_length=200, blank=True)
    date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    renewal_status = models.CharField(
        max_length=20, choices=RENEWAL_STATUS_CHOICES, default="not_required"
    )
    renewal_notes = models.TextField(blank=True)
    shared_with = models.CharField(max_length=500, blank=True)
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    share_enabled = models.BooleanField(default=False)
    share_download_enabled = models.BooleanField(default=False)
    share_expires_at = models.DateTimeField(null=True, blank=True)
    share_views = models.PositiveIntegerField(default=0)
    share_message = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            import mimetypes

            self.file_type = (
                mimetypes.guess_type(self.file.name)[0] or "application/octet-stream"
            )
        super().save(*args, **kwargs)

    def get_size_display(self):
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def file_format(self):
        """Return a compact display value such as PDF, PNG, or DOCX."""
        if self.file_type and "/" in self.file_type:
            return self.file_type.rsplit("/", 1)[-1].upper()
        if self.file:
            suffix = self.file.name.rsplit(".", 1)[-1] if "." in self.file.name else ""
            return suffix.upper() or "FILE"
        return "FILE"

    @property
    def days_until_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.localdate()).days

    @property
    def is_expired(self):
        days = self.days_until_expiry
        return days is not None and days < 0

    @property
    def is_expiring_soon(self):
        days = self.days_until_expiry
        return days is not None and 0 <= days <= 45

    @property
    def needs_renewal_attention(self):
        return (
            self.is_expired
            or self.is_expiring_soon
            or self.renewal_status == "needs_review"
        )

    def renewal_maps_url(self):
        from .services.renewal import renewal_map_url

        location = getattr(getattr(self.user, "profile", None), "location", "")
        return renewal_map_url(self, location)

    @property
    def public_share_is_expired(self):
        return bool(self.share_expires_at and self.share_expires_at <= timezone.now())

    @property
    def public_share_is_active(self):
        return self.share_enabled and not self.public_share_is_expired


class Appointment(models.Model):
    MODE_CHOICES = [
        ("teleconsultation", "Teleconsultation"),
        ("in_person", "In-Person"),
    ]
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="appointments"
    )
    doctor_name = models.CharField(max_length=200)
    department = models.CharField(max_length=200, blank=True)
    datetime = models.DateTimeField()
    mode = models.CharField(
        max_length=20, choices=MODE_CHOICES, default="teleconsultation"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="scheduled"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-datetime"]

    def __str__(self):
        return f"{self.doctor_name} - {self.datetime.strftime('%b %d, %Y %H:%M')}"


class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("closed", "Closed"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tickets")
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    admin_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.id} - {self.subject}"


class ChatMessage(models.Model):
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_messages",
        null=True,
        blank=True,
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("success", "Success"),
        ("error", "Error"),
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default="info"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ABHARecord(models.Model):
    RECORD_TYPE_CHOICES = [
        ("allergy", "Allergy"),
        ("medication", "Medication"),
        ("condition", "Medical Condition"),
        ("procedure", "Procedure"),
        ("immunization", "Immunization"),
        ("lab", "Lab Result"),
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="abha_records"
    )
    abha_id = models.CharField(max_length=50)
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES)
    data = models.JSONField(default=dict)
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-synced_at"]

    def __str__(self):
        return f"{self.record_type} - {self.abha_id}"


class SecurityLog(models.Model):
    STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
        ("warning", "Warning"),
    ]
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="security_logs",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="success")
    ip_address = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.title} - {self.status}"

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    source = models.CharField(max_length=80, default="footer")
    consent = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Newsletter subscriber"
        verbose_name_plural = "Newsletter subscribers"

    def __str__(self):
        return self.email


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=180)
    message = models.TextField()
    ip_address = models.CharField(max_length=50, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} — {self.email}"

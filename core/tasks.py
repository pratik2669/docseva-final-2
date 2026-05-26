from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.core.mail import mail_admins, send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_admin_notification(self, subject: str, message: str) -> int:
    """Send an admin alert email. Used for operational notifications."""
    mail_admins(subject=subject, message=message, fail_silently=False)
    logger.info("Admin notification sent: %s", subject)
    return 1


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_expiry_reminders(self) -> dict:
    """
    Daily task: email users whose documents expire within the next 30, 14,
    or 7 days. Skips documents with no expiry date or no linked user email.
    """
    from django.conf import settings
    from core.models import Document

    now = timezone.now().date()
    reminder_windows = [30, 14, 7]  # days before expiry
    sent = 0
    skipped = 0

    for days in reminder_windows:
        target_date = now + timedelta(days=days)
        expiring_docs = Document.objects.filter(
            expiry_date=target_date,
            user__email__isnull=False,
        ).select_related("user", "user__profile")

        for doc in expiring_docs:
            user = doc.user
            email = user.email
            if not email:
                skipped += 1
                continue

            name = getattr(user, "profile", None)
            display_name = name.name if name and name.name else user.username
            subject = f"DocSeva: '{doc.name}' expires in {days} day(s)"
            message = (
                f"Hi {display_name},\n\n"
                f"Your document '{doc.name}' is expiring on {doc.expiry_date}.\n"
                f"Please log in to DocSeva to renew or update it:\n"
                f"{getattr(settings, 'PUBLIC_BASE_URL', '')}/dashboard/\n\n"
                f"— The DocSeva Team"
            )

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                sent += 1
                logger.info(
                    "Expiry reminder sent to %s for document '%s' (expires %s, %d days)",
                    email,
                    doc.name,
                    doc.expiry_date,
                    days,
                )
            except Exception as exc:
                skipped += 1
                logger.error(
                    "Failed to send expiry reminder to %s for doc '%s': %s",
                    email,
                    doc.name,
                    exc,
                )

    result = {"sent": sent, "skipped": skipped}
    logger.info("Expiry reminder task complete: %s", result)
    return result

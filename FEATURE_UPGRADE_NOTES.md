# DocSeva Modern Feature Upgrade

This release upgrades the project from a prototype to a stronger deploy-ready base.

## Added

- Modern landing page and friendlier registration page.
- Separate DocSeva portal admin role using `UserProfile.is_portal_admin`.
- Emergency medical QR sharing with explicit user enable/disable.
- Document expiry dates, expiring soon alerts, expired document warnings.
- Renewal assistant with required document checklist and map search links.
- Secure expiring document share links with optional download permission.
- Public shared document metadata page and protected public download route.
- Portal admin UI cleanup so app admin is separate from Django superuser.

## Portal admin command

```bash
python manage.py promote_portal_admin username_or_email
```

## Production reminders

- Use `DEBUG=False`, PostgreSQL, HTTPS, and `collectstatic` in production.
- Configure real SMTP for password reset email.
- Replace mock ABHA/PM-JAY flows with official API clients before public claims.
- Use private/S3 media storage for real document storage at scale.

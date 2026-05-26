# DocSeva modern full feature upgrade

This package includes the requested production-base improvements:

## Portal roles

DocSeva now separates application roles into:

- User: normal user portal.
- Admin: operational admin portal.
- Super Admin: admin portal plus role-management rights.

These are separate from Django's technical `/admin/` superuser system.

Commands:

```bash
python manage.py set_portal_role username user
python manage.py set_portal_role username admin
python manage.py set_portal_role username superadmin
```

Backward-compatible command:

```bash
python manage.py promote_portal_admin username --role admin
python manage.py promote_portal_admin username --role superadmin
```

## Emergency QR

Users can enable emergency QR sharing from Profile. The QR points to a public emergency page that exposes only selected medical fields.

## Document renewal

Documents can store an expiry/renewal date. Expiring documents are shown on Dashboard and Documents. Renewal pages include:

- required documents checklist,
- renewal tracking status,
- renewal notes,
- Google Maps search link for renewal centers.

## Document sharing

Users can create secure public document share links with:

- optional expiry,
- optional download permission,
- recipient note,
- view counter,
- email-link helper.

## UI modernization

Landing, registration, dashboard, admin portal, documents, detail, renewal, sharing, and emergency pages have modern Tailwind-based layout/components.

## Production notes

The project is deploy-ready as a Django base, but production still requires real values in `.env`:

- strong SECRET_KEY,
- DEBUG=False,
- ALLOWED_HOSTS,
- CSRF_TRUSTED_ORIGINS,
- PostgreSQL DATABASE_URL,
- Redis REDIS_URL if needed,
- SMTP credentials for password reset,
- real ABHA/PM-JAY credentials if GOV_API_MODE=live.

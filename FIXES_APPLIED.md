# DocSeva — Fixes Applied & Deployment Guide

Generated: May 2026

---

## Bugs Fixed (Critical)

| # | Bug | File | Fix Applied |
|---|-----|------|-------------|
| 1 | `{% url 'security_log' %}` — NoReverseMatch | `dashboard.html:184` | Changed to `{% url 'security' %}` (correct URL name in urls.py) |
| 2 | `profile.profile_image` — wrong field name | `base.html:56-57` | Changed to `profile.image` (actual model field) |
| 3 | Mobile logout is a GET `<a href>` — CSRF bypass | `base.html:121` | Replaced with `<form method="post">{% csrf_token %}` |
| 4 | `CSPMiddleware` not in MIDDLEWARE — CSP_ vars had no effect | `settings.py` | Added `csp.middleware.CSPMiddleware` to MIDDLEWARE |
| 5 | CSP blocks Tailwind CDN + Lucide in production | `settings.py` | Added CDN domains to `CSP_SCRIPT_SRC`, `CSP_STYLE_SRC` |
| 6 | `profile` not in global context — avatar broken on non-profile pages | `context_processors.py` | Added `profile` to `docseva_context()` return dict |
| 7 | Procfile release missing `create_default_plans` | `Procfile` | Added to release command |
| 8 | `logout_view` accepts GET (security issue) | `views.py` | Added `@require_POST` decorator |
| 9 | Security link missing from navbar | `base.html` | Added Security nav link (desktop + mobile) |

---

## Security Issues (Fixed)

| Issue | Risk | Fix |
|-------|------|-----|
| GET logout | Medium – logout CSRF possible | `@require_POST` on logout_view + mobile POST form |
| CSP not active | High – XSS protection disabled | Added CSPMiddleware |
| Profile avatar broken | Low – UX only | Correct field name `image` |

---

## Security Issues (Remaining — To Do)

| Issue | Risk | Action Required |
|-------|------|----------------|
| Tailwind from CDN (`unsafe-inline` scripts) | Low-Medium | For full production hardening: self-host Tailwind CSS. CDN is fine for MVP. |
| Media files served by Django in dev | Low | In multi-instance production: add S3/Cloudflare R2 storage |
| No email verification on registration | Medium | Add `django-allauth` or custom email verification |
| No 2FA (field exists but no flow) | Medium | Implement TOTP using `django-otp` or `django-two-factor-auth` |
| `GOV_API_MODE=mock` — fake data | High (legal) | Must integrate real NHA APIs before live gov features |
| Password reset requires real SMTP | High | Configure `EMAIL_HOST` etc. before enabling password reset in prod |

---

## Deployment Checklist

### Phase 1 — Local Stable

```fish
cd "/home/diggerpuk/Projects/docseva 2.1/docseva_prod"
source .venv/bin/activate.fish
cp .env.example .env
# Edit .env: set DEBUG=True, generate SECRET_KEY
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py create_default_plans
python manage.py createsuperuser
python manage.py runserver
```

### Phase 2 — Verify Everything Works

```fish
python manage.py check
python manage.py test
# Visit http://127.0.0.1:8000 and test:
# - Register new account
# - Login / Logout (must use POST button, not GET link)
# - Upload document
# - View dashboard
# - Check security log link works (bottom of dashboard)
# - Profile image upload
# - Password reset flow (check terminal for email output)
# - Admin portal (promote user first: python manage.py set_portal_role USERNAME admin)
```

### Phase 3 — Production Deploy (Render.com)

1. Push this repo to GitHub (ensure `.env`, `db.sqlite3`, `.venv` are in `.gitignore`)
2. Create a Render Blueprint from `render.yaml`
3. Set these secrets in Render dashboard:
   - `ALLOWED_HOSTS` = `yourapp.onrender.com`
   - `CSRF_TRUSTED_ORIGINS` = `https://yourapp.onrender.com`
   - `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
4. Deploy — Render runs migrations + collectstatic automatically via Procfile
5. SSH into Render and create superuser:
   ```bash
   python manage.py createsuperuser
   ```
6. Visit `/portal/admin/` to access the admin portal

### Phase 4 — Production Checks

```fish
# Run Django's own deploy checklist
python manage.py check --deploy
```

Expected warnings to address:
- `SECURE_SSL_REDIRECT` — already True in production via settings.py
- `SESSION_COOKIE_SECURE` — already True in production
- `CSRF_COOKIE_SECURE` — already True in production

---

## URL Reference

| URL | Name | View | Auth |
|-----|------|------|------|
| `/` | `landing` | `landing_view` | Public |
| `/registration/` | `registration` | `registration_view` | Public |
| `/login/` | `login` | `login_view` | Public |
| `/logout/` | `logout` | `logout_view` | POST only |
| `/dashboard/` | `dashboard` | `dashboard_view` | Login required |
| `/documents/` | `document` | `document_view` | Login required |
| `/documents/upload/` | `upload` | `upload_view` | Login required, POST |
| `/documents/<pk>/` | `document_detail` | `document_detail_view` | Login required |
| `/documents/<pk>/download/` | `document_download` | `document_download_view` | Login required |
| `/documents/<pk>/share/` | `document_share` | `document_share_view` | Login required, POST |
| `/documents/<pk>/renew/` | `document_renewal` | `document_renewal_view` | Login required |
| `/documents/<pk>/delete/` | `document_delete` | `document_delete_view` | Login required, POST |
| `/s/document/<token>/` | `public_document_share` | `public_document_share_view` | Public |
| `/profile/` | `profile` | `profile_view` | Login required |
| `/profile/emergency-qr/` | `emergency_qr` | `emergency_qr_view` | Login required |
| `/emergency/<token>/` | `emergency_public` | `emergency_public_view` | Public |
| `/gov/` | `gov` | `gov_view` | Login required |
| `/support/` | `support` | `support_view` | Login required |
| `/security/` | `security` | `security_view` | Login required |
| `/search/` | `search` | `search_view` | Login required |
| `/portal/admin/` | `admin_dashboard` | `admin_dashboard_view` | Admin required |
| `/portal/admin/users/` | `admin_users` | `admin_user_list_view` | Admin required |
| `/portal/admin/tickets/` | `admin_tickets` | `admin_ticket_list_view` | Admin required |
| `/portal/admin/documents/` | `admin_documents` | `admin_document_list_view` | Admin required |
| `/portal/admin/security/` | `admin_security` | `admin_security_log_list_view` | Admin required |
| `/portal/admin/appointments/` | `admin_appointments` | `admin_appointment_list_view` | Admin required |
| `/healthz/` | `health_check` | `health_check` | Public |

---

## Recommended Production .env

```ini
DEBUG=False
SECRET_KEY=<generate: python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
ALLOWED_HOSTS=yourapp.onrender.com
CSRF_TRUSTED_ORIGINS=https://yourapp.onrender.com

DATABASE_URL=postgres://user:pass@host:5432/docseva
REDIS_URL=redis://host:6379/0

SECURE_SSL_REDIRECT=True
USE_X_FORWARDED_HOST=True

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<your_sendgrid_key>
DEFAULT_FROM_EMAIL=DocSeva <noreply@yourdomain.com>
ADMINS=admin@yourdomain.com

GOV_API_MODE=mock
RATELIMIT_ENABLE=True
LOG_LEVEL=INFO
GUNICORN_WORKERS=3
```

---

## Clean Project for GitHub

```fish
# Remove sensitive/generated files
rm -f .env db.sqlite3
rm -rf .venv/ staticfiles/ media/
find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
```

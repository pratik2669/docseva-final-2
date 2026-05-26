# DocSeva production checklist applied

## Implemented in this zip

- Environment-based `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.
- HTTPS production settings: SSL redirect, secure session/CSRF cookies, HSTS, frame denial, content sniffing protection, referrer policy.
- PostgreSQL support through `DATABASE_URL` and persistent connection age.
- Redis cache/session/rate-limit support through `REDIS_URL`.
- WhiteNoise static file serving with compressed manifest storage.
- Optional S3-compatible media storage with `USE_S3_MEDIA=True` and `django-storages`.
- Gunicorn, Dockerfile, docker-compose, Render blueprint, Procfile.
- Celery worker/beat scaffolding with Redis broker support.
- Structured production logging and optional Sentry integration.
- Health endpoint `/healthz/`, robots.txt, sitemap.xml, security.txt.
- Configurable hardened Django admin URL through `ADMIN_URL`.
- Cookie consent banner, dark mode, breadcrumbs, print stylesheet, loading skeletons.
- Legal/content pages: About, Pricing, Contact, FAQ, Resources, Privacy, Terms.
- Registration terms checkbox, password visibility toggle, password strength indicator.
- Newsletter signup model/form and contact message model/form.
- Open Graph image, logo, favicon, web manifest.
- JSON-LD for website/search, pricing, and FAQ pages.
- GitHub Actions CI with Django checks, collectstatic, tests, and coverage.
- Deployment examples for Nginx and systemd.
- PostgreSQL backup script.
- Split dependency files: `requirements/base.txt`, `requirements/prod.txt`, `requirements/dev.txt`.
- Code quality config: `pyproject.toml`, `.pre-commit-config.yaml`.

## Still requires real external setup

- Buy/connect real domain and update DNS.
- Create production PostgreSQL and Redis services.
- Add real SMTP credentials for password reset and alerts.
- Add Sentry DSN for error monitoring.
- Add real S3 bucket or keep single-server local media storage.
- Configure UptimeRobot/Pingdom or similar to monitor `/healthz/`.
- Configure scheduled backups outside the app container.
- Replace template Privacy/Terms text with legal-review-ready text before real users.
- Connect real government APIs only after approval and compliance review.
- Add admin 2FA provider if required by your hosting/compliance policy; profile field exists, but full OTP enforcement needs a provider decision.

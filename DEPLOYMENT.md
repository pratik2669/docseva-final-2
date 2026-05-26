# DocSeva – Deployment Guide

## Quick-start (local development)

```bash
# 1. Clone and enter the project
git clone <your-repo> docseva && cd docseva

# 2. Create and activate a virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env – set DEBUG=True, leave DATABASE_URL empty for SQLite

# 5. Migrate and seed data
python manage.py migrate
python manage.py create_default_plans
python manage.py createsuperuser

# 6. Run the dev server
python manage.py runserver
# Visit http://localhost:8000
```

---

## Docker Compose (local / staging)

```bash
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD and SECRET_KEY at minimum

docker compose up --build -d
docker compose logs -f web
```

---

## Render.com (recommended production path)

1. Push your repo to GitHub.
2. In Render, choose **New → Blueprint** and point it at your repo.
3. Render reads `render.yaml` and creates the web service, Postgres, and Redis automatically.
4. In the web service's **Environment** tab, fill in the `sync: false` variables:
   - `ALLOWED_HOSTS` → `yourdomain.onrender.com`
   - `CSRF_TRUSTED_ORIGINS` → `https://yourdomain.onrender.com`
   - `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
   - `DEFAULT_FROM_EMAIL`
   - `ADMINS` (comma-separated email addresses for error alerts)
5. Deploy. Render automatically runs migrations and collects static files via `entrypoint.sh`.

---

## Environment variables reference

See `.env.example` for the full list with descriptions.

### Minimum required in production

| Variable | Description |
|---|---|
| `SECRET_KEY` | Long random string – never reuse |
| `DEBUG` | Must be `False` |
| `ALLOWED_HOSTS` | Your domain(s), comma-separated |
| `CSRF_TRUSTED_ORIGINS` | Your https:// origin(s) |
| `DATABASE_URL` | PostgreSQL connection string |

---

## Security checklist before going live

- [ ] `DEBUG=False`
- [ ] Strong `SECRET_KEY` (min 50 chars, random)
- [ ] `ALLOWED_HOSTS` contains only your domain(s)
- [ ] `CSRF_TRUSTED_ORIGINS` set to `https://yourdomain`
- [ ] `SECURE_SSL_REDIRECT=True` (HTTPS enforced)
- [ ] `EMAIL_BACKEND` set to SMTP (not console)
- [ ] `ADMINS` set to receive 500-error emails
- [ ] `RATELIMIT_ENABLE=True`
- [ ] `CSP_REPORT_ONLY=False`
- [ ] Redis configured (`REDIS_URL`) for production sessions/cache
- [ ] Ran `python manage.py check --deploy` with no errors

---

## Management commands

```bash
# Seed default subscription plans (idempotent – safe to re-run)
python manage.py create_default_plans

# Run all tests
python manage.py test core --verbosity=2

# Django deployment checks
python manage.py check --deploy
```

---

## Health endpoints

| Path | Description |
|---|---|
| `/healthz/` | Simple liveness check (returns `{"status":"ok"}`) |
| `/ht/` | django-health-check: DB, cache, storage, migrations |

Configure your load balancer / uptime monitor to poll `/healthz/`.

---

## Logging

- **Development** (`DEBUG=True`): human-readable console output.
- **Production** (`DEBUG=False`): structured JSON (compatible with Papertrail, Datadog, Loki, etc.).

Set `LOG_LEVEL=DEBUG` temporarily to increase verbosity.

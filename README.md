# DocSeva — Secure Document Vault

A production-ready Django web app for citizens and healthcare workers to securely manage vital documents, track renewals, and share records via tamper-safe QR links.

---

## Quick Start (Local Development)

```fish
# 1. Clone and enter the project
cd "/home/youruser/Projects/docseva 2.1/docseva_prod"

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate.fish

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env: set DEBUG=True, set a SECRET_KEY

# 5. Run migrations
python manage.py migrate

# 6. Seed default subscription plans
python manage.py create_default_plans

# 7. Create a superuser
python manage.py createsuperuser

# 8. Start the development server
python manage.py runserver
```

Open http://127.0.0.1:8000

---

## Features

| Feature | Description |
|---|---|
| Document Vault | Upload, categorize, search, download documents |
| Renewal Tracker | Expiry alerts and renewal guidance per document type |
| Public Share Links | Time-limited, tokenized document sharing |
| Emergency QR | Medical info QR that works offline |
| Support Tickets | User-to-admin ticketing with live chat |
| Gov Hub | ABHA ID linking, appointment booking (mock mode) |
| Admin Portal | Role-separated admin dashboard (admin / superadmin) |
| Security Logs | Audit trail of all user actions |

---

## User Roles

| Role | Access |
|---|---|
| `user` | Own vault only |
| `admin` | Portal dashboard, all tickets/docs/users (read + respond) |
| `superadmin` | Full control including role changes |

Promote a user via the Django shell or management command:

```fish
python manage.py set_portal_role USERNAME superadmin
```

---

## Environment Variables

See `.env.example` for the full reference.  
Key variables for production:

```ini
DEBUG=False
SECRET_KEY=<generate with python manage.py shell>
ALLOWED_HOSTS=yourdomain.onrender.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.onrender.com
DATABASE_URL=postgres://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<sendgrid_api_key>
```

---

## Deployment on Render

1. Push code to GitHub (make sure `.env` is in `.gitignore`).
2. Create a new Blueprint on [render.com](https://render.com) pointing at your repo.
3. Render reads `render.yaml` and provisions: **web service**, **PostgreSQL**, **Redis**.
4. Set the `sync: false` variables in the Render dashboard:
   - `ALLOWED_HOSTS`
   - `CSRF_TRUSTED_ORIGINS`
   - `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
5. The `Procfile` release command runs migrations, seeds plans, and collects static automatically.

---

## Docker

```bash
# Build and run locally with Docker Compose
docker compose up --build

# Or build standalone
docker build -t docseva .
docker run -p 8000:8000 --env-file .env docseva
```

---

## Management Commands

| Command | Purpose |
|---|---|
| `python manage.py migrate` | Apply database migrations |
| `python manage.py create_default_plans` | Seed Free/Pro/Elite plans |
| `python manage.py collectstatic` | Gather static files for production |
| `python manage.py createsuperuser` | Create a Django superuser |
| `python manage.py set_portal_role USERNAME ROLE` | Set portal role (user/admin/superadmin) |
| `python manage.py check --deploy` | Run Django deployment checks |

---

## Project Structure

```
docseva_prod/
├── docseva/            # Django project config
│   ├── settings.py     # All settings (env-driven)
│   └── urls.py         # Root URL conf
├── core/               # Main app
│   ├── models.py       # UserProfile, Document, SupportTicket, SecurityLog…
│   ├── views.py        # All views
│   ├── urls.py         # URL patterns
│   ├── forms.py        # All forms
│   ├── context_processors.py  # Global template context
│   ├── templates/      # All HTML templates
│   ├── static/         # CSS
│   └── management/commands/  # Custom management commands
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── render.yaml         # Render.com blueprint
└── Procfile            # Heroku/Railway/Render release commands
```

---

## Known Limitations / Demo Mode

- **Government API** (ABHA, Ayushman): mock responses only. Set `GOV_API_MODE=live` and wire up real NHA APIs before production use.
- **Media files**: stored on local disk. For multi-instance production deployments, use S3-compatible storage.
- **Email**: defaults to console backend. Configure SMTP for password resets in production.

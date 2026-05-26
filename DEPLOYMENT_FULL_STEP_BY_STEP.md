# DocSeva deployment step by step

## Option A — Render web service + managed PostgreSQL

1. Push the project to GitHub.
2. On Render, create a PostgreSQL database.
3. Create a Web Service from the repository.
4. Set build command:
   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput
   ```
5. Set start command:
   ```bash
   gunicorn docseva.wsgi:application --bind 0.0.0.0:$PORT
   ```
6. Add environment variables:
   ```env
   SECRET_KEY=<new Django secret>
   DEBUG=False
   ALLOWED_HOSTS=<your-service>.onrender.com,docseva.in,www.docseva.in
   CSRF_TRUSTED_ORIGINS=https://<your-service>.onrender.com,https://docseva.in,https://www.docseva.in
   DATABASE_URL=<Render PostgreSQL internal URL>
   DATABASE_SSL_REQUIRE=True
   SECURE_SSL_REDIRECT=True
   PUBLIC_BASE_URL=https://<your-service>.onrender.com
   ADMIN_URL=<hard-to-guess-admin-path>/
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=<smtp host>
   EMAIL_HOST_USER=<smtp user>
   EMAIL_HOST_PASSWORD=<smtp password>
   DEFAULT_FROM_EMAIL=DocSeva <noreply@docseva.in>
   SERVER_EMAIL=errors@docseva.in
   ```
7. Run one-time commands in Render shell:
   ```bash
   python manage.py migrate
   python manage.py create_default_plans
   python manage.py createsuperuser
   python manage.py set_portal_role <username> superadmin
   ```
8. Open `/healthz/`. It should return `{"status":"ok","service":"docseva"}`.
9. Open the site URL. If it fails, check logs for the first red traceback line.
10. After custom domain is connected, update `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `PUBLIC_BASE_URL` to the real domain.

## Option B — VPS with Nginx + Gunicorn + systemd

1. Install Python 3.12, PostgreSQL, Redis, Nginx, Certbot.
2. Create `/srv/docseva/current` and copy the project.
3. Create venv and install production dependencies:
   ```bash
   python3.12 -m venv /srv/docseva/venv
   /srv/docseva/venv/bin/pip install -r requirements/prod.txt
   ```
4. Create `/srv/docseva/.env` from `.env.example` and set production values.
5. Run:
   ```bash
   /srv/docseva/venv/bin/python manage.py migrate
   /srv/docseva/venv/bin/python manage.py collectstatic --noinput
   /srv/docseva/venv/bin/python manage.py create_default_plans
   ```
6. Copy `deploy/systemd/docseva.service` to `/etc/systemd/system/` and enable it.
7. Copy `deploy/nginx/docseva.conf` to `/etc/nginx/sites-available/`, edit domain paths, enable it.
8. Issue SSL certificate with Certbot.
9. Enable monitoring against `https://yourdomain/healthz/`.
10. Schedule `scripts/backup_postgres.sh` using cron or a managed backup service.

## Local production-like Docker test

```bash
cp .env.example .env
# edit SECRET_KEY, DEBUG=False, ALLOWED_HOSTS, CSRF origins
POSTGRES_PASSWORD=change_this docker compose up --build
```

Then open `http://localhost:8000/healthz/`.

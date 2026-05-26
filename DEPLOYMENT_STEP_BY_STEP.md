# DocSeva Deployment Guide

This guide assumes the project root is `docseva_fixed`.

## 1. Run locally first

```bash
cd ~/Projects/docseva_fixed
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.local.example .env
python manage.py migrate
python manage.py create_default_plans
python manage.py createsuperuser
python manage.py test
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## 2. Local LAN sharing / QR testing

Find your laptop IP:

```bash
hostname -I | awk '{print $1}'
```

Edit `.env`:

```env
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,YOUR_LAPTOP_IP
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://YOUR_LAPTOP_IP:8000
PUBLIC_BASE_URL=http://YOUR_LAPTOP_IP:8000
```

Run:

```bash
python manage.py runserver 0.0.0.0:8000
```

Phone URL on same Wi-Fi:

```text
http://YOUR_LAPTOP_IP:8000/
```

## 3. GitHub push

```bash
cd ~/Projects/docseva_fixed
git init
git add .
git commit -m "make DocSeva production deployable"
git branch -M main
git remote add origin git@github.com:YOUR_USERNAME/docseva.git
git push -u origin main
```

If the remote already exists:

```bash
git remote set-url origin git@github.com:YOUR_USERNAME/docseva.git
git push -u origin main
```

## 4. Render deployment using `render.yaml`

1. Push this project to GitHub.
2. Open Render Dashboard.
3. Choose **New > Blueprint**.
4. Connect the GitHub repository.
5. Select the root `render.yaml`.
6. Fill the variables marked `sync: false`:

```env
ALLOWED_HOSTS=YOUR_SERVICE_NAME.onrender.com
CSRF_TRUSTED_ORIGINS=https://YOUR_SERVICE_NAME.onrender.com
PUBLIC_BASE_URL=https://YOUR_SERVICE_NAME.onrender.com
EMAIL_HOST=smtp.example.com
EMAIL_HOST_USER=your_smtp_user
EMAIL_HOST_PASSWORD=your_smtp_password_or_api_key
DEFAULT_FROM_EMAIL=DocSeva <noreply@yourdomain.com>
ADMINS=your_email@example.com
SECURITY_CONTACT=mailto:security@yourdomain.com
```

The Docker entrypoint runs:

```bash
python manage.py migrate --noinput
python manage.py create_default_plans
python manage.py collectstatic --noinput --clear
```

Then Gunicorn starts the app.

## 5. After first deploy

Open Render Shell or run a one-off job:

```bash
python manage.py createsuperuser
python manage.py set_portal_role YOUR_USERNAME superadmin
```

Verify:

```text
https://YOUR_SERVICE_NAME.onrender.com/healthz/
https://YOUR_SERVICE_NAME.onrender.com/
https://YOUR_SERVICE_NAME.onrender.com/portal/admin/
```

## 6. Production environment checklist

```env
DEBUG=False
SECRET_KEY=<strong generated key>
ALLOWED_HOSTS=<your-domain>
CSRF_TRUSTED_ORIGINS=https://<your-domain>
PUBLIC_BASE_URL=https://<your-domain>
DATABASE_SSL_REQUIRE=True
SECURE_SSL_REDIRECT=True
USE_X_FORWARDED_HOST=True
RATELIMIT_ENABLE=True
GOV_API_MODE=mock
```

Generate a strong secret locally:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 7. Final checks before launch

```bash
python manage.py check --deploy
python manage.py test
python manage.py collectstatic --noinput
```

## 8. Things not to skip

- Do not deploy with `DEBUG=True`.
- Do not commit `.env`.
- Do not use SQLite in production.
- Do not advertise ABHA/Ayushman as live until official APIs are connected.
- Set real SMTP credentials or password reset emails will not reach users.
- Set backups for PostgreSQL and uploaded media.

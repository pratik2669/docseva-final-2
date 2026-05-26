# DocSeva Local + Render Setup

## Local development

```bash
cd /path/to/docseva_fixed
cp .env.local.example .env
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py create_default_plans
python manage.py createsuperuser
python manage.py runserver
```

For fish shell:

```fish
cd /path/to/docseva_fixed
cp .env.local.example .env
python -m venv .venv
source .venv/bin/activate.fish
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py create_default_plans
python manage.py createsuperuser
python manage.py runserver
```

## Admin role after first deploy

Django `createsuperuser` only creates a Django admin account. To make that same user a DocSeva portal superadmin, run:

```bash
python manage.py set_portal_role USERNAME superadmin
```

Use the real username you created with `createsuperuser`.

## Password reset email

Local mode uses:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

This prints reset emails in the terminal. Production must use SMTP:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<smtp-host>
EMAIL_PORT=587
EMAIL_HOST_USER=<smtp-user>
EMAIL_HOST_PASSWORD=<smtp-password-or-api-key>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=DocSeva <noreply@yourdomain.com>
```

## Render domain variables

After Render gives you a domain, set:

```env
ALLOWED_HOSTS=<your-service-name>.onrender.com
CSRF_TRUSTED_ORIGINS=https://<your-service-name>.onrender.com
```

Do not include `https://` in `ALLOWED_HOSTS`. Do include `https://` in `CSRF_TRUSTED_ORIGINS`.

## Government API mode

Keep this until official NHA/ABHA API integration is implemented:

```env
GOV_API_MODE=mock
```

The current GOV Hub stores ABHA ID locally and creates demo records only. It must not be represented as live NHA/ABHA verification.

## Local QR scanning from another phone

A phone cannot open `localhost` from your laptop. For QR scan testing on the same Wi-Fi:

```bash
hostname -I | awk '{print $1}'
```

Put that IP in `.env`:

```env
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,YOUR_LAPTOP_IP
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://YOUR_LAPTOP_IP:8000
PUBLIC_BASE_URL=http://YOUR_LAPTOP_IP:8000
```

Run Django on all network interfaces:

```bash
python manage.py runserver 0.0.0.0:8000
```

Or use the helper script:

```bash
./scripts/run_lan.sh
```

Then open `http://YOUR_LAPTOP_IP:8000/profile/emergency-qr/` on the laptop or phone. The QR will point to the same LAN address and another phone on the same Wi-Fi will show the emergency data page.

Required conditions:

- The laptop and phone must be on the same Wi-Fi.
- The laptop firewall must allow port `8000`.
- Emergency sharing must be enabled in Profile.
- Emergency fields must be filled; otherwise the public page intentionally shows an empty-data notice.

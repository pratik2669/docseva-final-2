# DocSeva Professional Deployable Patch

## What was improved

- Added public professional pages: About, Contact, Privacy Policy, and Terms of Service.
- Added real footer links instead of placeholder `#` links.
- Added unauthenticated navigation links for About and Contact.
- Added a landing-page workflow section to make the product easier for beginners to understand.
- Added sitemap entries for public information pages.
- Added rate limiting to public emergency QR pages, public document share pages, public document downloads, support chat sends, ABHA sync, and Ayushman eligibility checks.
- Added PUBLIC_BASE_URL validation so bad QR/share base URLs fail fast during startup.
- Added `SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"` for stronger browser isolation.
- Added a copy-to-clipboard toast and Escape-key behavior for mobile menu/notification panels.
- Added mobile admin/sidebar CSS improvements.
- Added public-page tests.
- Reformatted Python files with Black for consistent code alignment.

## Validation completed

The patched project was validated with:

```bash
DEBUG=True SECRET_KEY=check-only python manage.py check
DEBUG=True SECRET_KEY=check-only python manage.py test -v 1
DEBUG=False SECRET_KEY='test-prod-secret-key-with-more-than-fifty-characters-123456789' \
  ALLOWED_HOSTS='example.com' \
  CSRF_TRUSTED_ORIGINS='https://example.com' \
  PUBLIC_BASE_URL='https://example.com' \
  python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python -m compileall -q .
```

Result: all checks passed, all 19 tests passed, no missing migrations were detected.

## Production notes still requiring real values

Before serving real users, set these in the hosting dashboard or `.env`:

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `PUBLIC_BASE_URL`
- `DATABASE_URL`
- `REDIS_URL`
- SMTP values: `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`
- `SECURITY_CONTACT`

## Important limitation

The ABHA and Ayushman flows are intentionally mock/demo flows while `GOV_API_MODE=mock`. Do not present them as live government integrations until approved official API access is implemented.

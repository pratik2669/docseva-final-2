#!/usr/bin/env sh
# DocSeva production entrypoint
# Runs migrations, seeds data, collects static files, then hands off to CMD.
# Safe to run for both web service and Celery workers.
set -e

echo "[entrypoint] ==============================="
echo "[entrypoint] DocSeva starting up..."
echo "[entrypoint] ==============================="

# ── Wait for the database to be ready (up to 30s) ────────────────────────────
echo "[entrypoint] Waiting for database..."
python - <<'EOF'
import os, time, sys
import dj_database_url
import psycopg

db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    print("[entrypoint] No DATABASE_URL set, skipping DB wait.")
    sys.exit(0)

cfg = dj_database_url.parse(db_url)
for attempt in range(30):
    try:
        conn = psycopg.connect(
            host=cfg.get("HOST", "localhost"),
            port=cfg.get("PORT", 5432),
            dbname=cfg.get("NAME", "postgres"),
            user=cfg.get("USER", "postgres"),
            password=cfg.get("PASSWORD", ""),
            connect_timeout=2,
        )
        conn.close()
        print(f"[entrypoint] Database ready after {attempt + 1} attempt(s).")
        sys.exit(0)
    except Exception as e:
        print(f"[entrypoint] DB not ready (attempt {attempt + 1}/30): {e}")
        time.sleep(2)

print("[entrypoint] ERROR: Database not ready after 60s. Aborting.")
sys.exit(1)
EOF

# ── Run all migrations (including django_celery_beat & django_celery_results) ─
echo "[entrypoint] Running database migrations..."
python manage.py migrate --noinput

# ── Seed default subscription plans ──────────────────────────────────────────
echo "[entrypoint] Seeding default subscription plans..."
python manage.py create_default_plans

# ── Collect static files (web service only — skip for Celery workers) ─────────
if [ "${SKIP_COLLECTSTATIC:-False}" != "True" ]; then
    echo "[entrypoint] Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi

echo "[entrypoint] Startup complete. Handing off to: $@"
exec "$@"


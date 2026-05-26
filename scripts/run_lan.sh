#!/usr/bin/env bash
set -euo pipefail

LAN_IP="${1:-$(hostname -I | awk '{print $1}')}"
if [[ -z "${LAN_IP}" ]]; then
  echo "Could not detect LAN IP. Run: scripts/run_lan.sh YOUR_LAPTOP_IP" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.local.example .env
fi

python - <<PY
from pathlib import Path
path = Path('.env')
text = path.read_text()
updates = {
    'ALLOWED_HOSTS': f'localhost,127.0.0.1,0.0.0.0,${LAN_IP}',
    'CSRF_TRUSTED_ORIGINS': f'http://localhost:8000,http://127.0.0.1:8000,http://${LAN_IP}:8000',
    'PUBLIC_BASE_URL': f'http://${LAN_IP}:8000',
}
lines = text.splitlines()
seen = set()
out = []
for line in lines:
    if '=' in line and not line.lstrip().startswith('#'):
        key = line.split('=', 1)[0].strip()
        if key in updates:
            out.append(f'{key}={updates[key]}')
            seen.add(key)
            continue
    out.append(line)
for key, value in updates.items():
    if key not in seen:
        out.append(f'{key}={value}')
path.write_text('\n'.join(out).rstrip() + '\n')
PY

echo "LAN URL: http://${LAN_IP}:8000"
echo "QR/share base URL has been written to .env"
echo "Phone and laptop must be on the same Wi-Fi."
python manage.py runserver 0.0.0.0:8000

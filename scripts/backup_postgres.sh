#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/docseva-$STAMP.dump"
pg_dump "$DATABASE_URL" --format=custom --no-owner --no-acl --file "$OUT"
find "$BACKUP_DIR" -type f -name 'docseva-*.dump' -mtime +"$RETENTION_DAYS" -delete
printf 'Backup written: %s\n' "$OUT"

#!/bin/sh
set -eu

HOST="${POSTGRES_HOST:-postgres}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-hawatch}"
LOG_DIR="${HAWATCH_LOG_DIR:-/var/log/hawatch}"
LOG_FILE="${HAWATCH_LOG_FILE:-${LOG_DIR}/api.jsonl}"

mkdir -p "$LOG_DIR"

log_info() {
  line="$(python -c 'import json,sys; print(json.dumps({"@timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), "level": "INFO", "service": "hawatch-api", "event": sys.argv[1]}, ensure_ascii=False))' "$1")"
  printf '%s\n' "$line"
  printf '%s\n' "$line" >> "$LOG_FILE"
}

log_info "startup.waiting_for_postgres"
i=0
until pg_isready -h "$HOST" -p "$PORT" -U "$USER" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 60 ]; then
    log_info "startup.postgres_timeout"
    exit 1
  fi
  sleep 2
done

log_info "startup.migrations_started"
python manage.py migrate --noinput

if [ "${DEMO_DATA_ENABLED:-true}" = "true" ]; then
  log_info "startup.demo_seed_started"
  python manage.py seed_demo_data
else
  # Catalog-only bootstrap for live mode — never calls Open-Meteo.
  echo "Ensuring Tochal catalog (DEMO_DATA_ENABLED=false)..."
  python manage.py seed_tochal_catalog
fi

log_info "startup.api_started"
exec gunicorn hawatch.config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout 60 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile -

#!/bin/sh
set -eu

run_gunicorn() {
  workers="${GUNICORN_WORKERS:-3}"
  threads="${GUNICORN_THREADS:-2}"
  for count in "$workers" "$threads"; do
    case "$count" in
      ''|*[!0-9]*) printf '%s\n' 'Gunicorn workers/threads must be positive integers.' >&2; exit 1 ;;
    esac
    [ "$count" -gt 0 ] || { printf '%s\n' 'Gunicorn workers/threads must be positive integers.' >&2; exit 1; }
  done
  exec gunicorn hawatch.config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$workers" \
    --worker-class gthread \
    --threads "$threads" \
    --keep-alive 5 \
    --timeout 60 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile - "$@"
}

# Exercise the exact serving arguments in a candidate image without waiting
# for PostgreSQL, running migrations or starting a listening worker.
if [ "${1:-}" = "--check-gunicorn" ]; then
  run_gunicorn --check-config
fi

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

log_info "startup.collectstatic_started"
python manage.py collectstatic --noinput

if [ "${DEMO_DATA_ENABLED:-true}" = "true" ]; then
  log_info "startup.demo_seed_started"
  python manage.py seed_demo_data
else
  # Live mode: bootstrap every packaged catalog only when DB has no live
  # points. Never re-sync or prune catalog data on a normal restart.
  if [ "${HAWATCH_BOOTSTRAP_LIVE_CATALOG_IF_EMPTY:-true}" = "true" ]; then
    log_info "startup.live_catalog_bootstrap_check"
    python manage.py bootstrap_live_catalog_if_empty --all
  else
    log_info "startup.live_catalog_bootstrap_skipped"
  fi
fi

if [ "$#" -gt 0 ]; then
  log_info "startup.command_started"
  exec "$@"
fi

log_info "startup.api_started"
run_gunicorn

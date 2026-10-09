#!/usr/bin/env bash
set -Eeuo pipefail
# Deploy only independent staging services; never run production migrations.
STAGE_DIR="${HAWATCH_STAGE_DIR:-/root/hawatch-stage}"
STAGE_ENV="${HAWATCH_STAGE_ENV_FILE:-/root/hawatch-stage.env}"
MODE="${1:-deploy}"
fail() { printf '[hawatch-stage] ERROR: %s\n' "$*" >&2; exit 1; }
[[ "$MODE" == deploy || "$MODE" == prepare || "$MODE" == activate ]] || fail "Usage: $0 [deploy|prepare|activate]"
[[ -d "$STAGE_DIR" && -f "$STAGE_ENV" ]] || fail "Prepare stage checkout and environment file first."
enabled="$(awk -F= '$1 == "HAWATCH_STAGE_ENABLED" {gsub(/[[:space:]\r]/, "", $2); print $2; exit}' "$STAGE_ENV")"
[[ "$enabled" == "1" ]] || fail "Stage is disabled in $STAGE_ENV."
[[ "$(git -C "$STAGE_DIR" branch --show-current)" == stage ]] || fail "Stage checkout must be on branch stage."
[[ -z "$(git -C "$STAGE_DIR" status --porcelain)" ]] || fail "Stage checkout contains uncommitted changes; nothing was reset."
[[ "$(git -C "$STAGE_DIR" remote get-url origin)" =~ ^(git@github.com:smmtaheri/hawatch.git|https://github.com/smmtaheri/hawatch.git)$ ]] || fail "Unexpected stage remote."
git -C "$STAGE_DIR" pull --ff-only origin stage
cd "$STAGE_DIR"
export HAWATCH_STAGE_ENV_FILE="$STAGE_ENV"
export HAWATCH_STAGE_IMAGE_TAG="$(git rev-parse --short=12 HEAD)"
compose=(docker compose --project-name hawatch-stage --env-file "$STAGE_ENV" -f infra/compose/compose.stage.yaml)
# Validate without printing resolved production database credentials.
"${compose[@]}" config --quiet
stage_port="$(awk -F= '$1 == "HAWATCH_STAGE_PORT" {gsub(/[[:space:]\r]/, "", $2); print $2; exit}' "$STAGE_ENV")"
stage_port="${stage_port:-5050}"
[[ "$stage_port" == 5050 ]] || fail "Stage must use port 5050; set HAWATCH_STAGE_PORT=5050."

if [[ "$MODE" != activate ]]; then
  attempt=0
  until "${compose[@]}" build stage-api stage-web; do
    attempt=$((attempt + 1))
    [[ "$attempt" -lt "${DOCKER_BUILD_RETRIES:-2}" ]] || fail "Stage build failed; existing stage containers were retained."
    sleep 5
  done
fi

if [[ "$MODE" == prepare ]]; then
  printf '[hawatch-stage] Images for %s built; existing stage containers were left untouched.\n' "$HAWATCH_STAGE_IMAGE_TAG"
  exit 0
fi

if [[ "$MODE" == activate ]]; then
  for image in "hawatch-stage-api:${HAWATCH_STAGE_IMAGE_TAG}" "hawatch-stage-web:${HAWATCH_STAGE_IMAGE_TAG}"; do
    docker image inspect "$image" >/dev/null 2>&1 || fail "Prepared stage image is missing: $image"
  done
fi

"${compose[@]}" up -d --wait stage-postgres stage-redis
"${compose[@]}" run --rm --no-deps --entrypoint python stage-api manage.py migrate --noinput
if [[ "$("${compose[@]}" run --rm --no-deps --entrypoint python stage-api manage.py shell -c 'from hawatch.modules.forecasts.models import WeatherPoint; print(WeatherPoint.objects.count())' | tail -n1)" == 0 ]]; then
  snapshot="$(mktemp)"
  trap 'rm -f "$snapshot"' EXIT
  # Production is read-only here: export only weather/catalog models, never users or proxy secrets.
  docker compose --project-directory "${HAWATCH_PRODUCTION_DIR:-/root/hawatch}" --env-file "${HAWATCH_PRODUCTION_DIR:-/root/hawatch}/.env" -f "${HAWATCH_PRODUCTION_DIR:-/root/hawatch}/infra/compose/compose.yaml" exec -T -i api python -c 'import django,sys; django.setup(); exec(sys.stdin.read())' < scripts/export-stage-data.py > "$snapshot"
  "${compose[@]}" run --rm --no-deps -i -T --entrypoint python stage-api manage.py import_stage_data < "$snapshot"
fi
"${compose[@]}" run --rm --no-deps --entrypoint python stage-api manage.py apply_route_descent
"${compose[@]}" run --rm --no-deps --entrypoint python stage-api manage.py ingest_open_meteo
"${compose[@]}" up -d --no-build --force-recreate stage-api stage-web stage-gateway stage-scheduler

wait_for_healthy() {
  local service="$1" container_id="" state="" health=""
  for _ in {1..150}; do
    container_id="$("${compose[@]}" ps -q "$service" 2>/dev/null || true)"
    if [[ -n "$container_id" ]]; then
      state="$(docker inspect --format '{{.State.Status}}' "$container_id" 2>/dev/null || true)"
      health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id" 2>/dev/null || true)"
      [[ "$state" != exited && "$state" != dead ]] || break
      [[ "$state" == running && "$health" == healthy ]] && return 0
    fi
    sleep 2
  done
  "${compose[@]}" logs --tail=100 "$service" >&2 || true
  fail "Stage service $service did not become healthy."
}

for service in stage-api stage-web stage-gateway; do
  wait_for_healthy "$service"
done

stage_bind_ip="$(awk -F= '$1 == "HAWATCH_STAGE_BIND_IP" {gsub(/[[:space:]\r]/, "", $2); print $2; exit}' "$STAGE_ENV")"
case "${stage_bind_ip:-0.0.0.0}" in
  0.0.0.0|127.0.0.1) stage_probe_host=127.0.0.1 ;;
  *) stage_probe_host="$stage_bind_ip" ;;
esac
stage_base="http://${stage_probe_host}:${stage_port}"
ready=0
for attempt in {1..30}; do
  if curl --fail --silent --show-error --max-time 3 "${stage_base}/healthz" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
[[ "$ready" == "1" ]] || fail "Stage gateway on port ${stage_port} did not become healthy."
curl --fail --silent --show-error --max-time 10 "${stage_base}/api/v1/health/ready/" >/dev/null || fail "Stage API readiness check failed through the gateway."
curl --fail --silent --show-error --max-time 15 "${stage_base}/" >/dev/null || fail "Stage server-rendered home page failed through the gateway."
curl --fail --silent --show-error --max-time 10 "${stage_base}/api/v1/points/" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
points = payload.get("results", payload if isinstance(payload, list) else [])
if not points or not any(point.get("data_mode") == "live" for point in points):
    raise SystemExit("Stage API returned no live catalog points from the isolated stage database.")
'
curl --fail --silent --show-error --max-time 15 "${stage_base}/api/v1/points/tochal/forecast/" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
meta = payload.get("meta", {})
if payload.get("empty") or meta.get("data_mode") != "live" or meta.get("provider") != "open-meteo" or not payload.get("hourly"):
    raise SystemExit("Stage forecast is not populated with live Open-Meteo data.")
'
curl --fail --silent --show-error --max-time 30 "${stage_base}/api/v1/points/tochal/forecast/week/" | python3 -c '
import json,sys
payload=json.load(sys.stdin)
if len(payload.get("days", [])) != 8 or payload.get("data_mode") != "live" or not payload.get("last_generated_at"):
    raise SystemExit("Stage weekly point forecast is not ready.")
'
curl --fail --silent --show-error --max-time 30 "${stage_base}/api/v1/routes/tochal-darband/forecast/week/" | python3 -c '
import json,sys
payload=json.load(sys.stdin)
if len(payload.get("days", [])) != 8 or len(payload.get("plans", {})) != 576 or not payload.get("records") or "descent_m" not in payload.get("subject", {}):
    raise SystemExit("Stage weekly route forecast is not ready.")
'

"${compose[@]}" ps

stage_origin="$(awk -F= '$1 == "HAWATCH_STAGE_ORIGIN" {print $2; exit}' "$STAGE_ENV")"
printf '[hawatch-stage] Ready: %s\n' "$stage_origin"

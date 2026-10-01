#!/usr/bin/env bash
set -Eeuo pipefail
# Deploy the optional stage stack only. It shares production's real database,
# while avoiding production's migration, bootstrap and ingest entrypoints.
STAGE_DIR="${HAWATCH_STAGE_DIR:-/root/hawatch-stage}"
STAGE_ENV="${HAWATCH_STAGE_ENV_FILE:-/root/hawatch-stage.env}"
fail() { printf '[hawatch-stage] ERROR: %s\n' "$*" >&2; exit 1; }
[[ -d "$STAGE_DIR" && -f "$STAGE_ENV" ]] || fail "Prepare stage checkout and environment file first."
enabled="$(awk -F= '$1 == "HAWATCH_STAGE_ENABLED" {gsub(/[[:space:]\r]/, "", $2); print $2; exit}' "$STAGE_ENV")"
[[ "$enabled" == "1" ]] || fail "Stage is disabled in $STAGE_ENV."
[[ "$(git -C "$STAGE_DIR" branch --show-current)" == stage ]] || fail "Stage checkout must be on branch stage."
[[ -z "$(git -C "$STAGE_DIR" status --porcelain)" ]] || fail "Stage checkout contains uncommitted changes; nothing was reset."
[[ "$(git -C "$STAGE_DIR" remote get-url origin)" =~ ^(git@github.com:smmtaheri/hawatch.git|https://github.com/smmtaheri/hawatch.git)$ ]] || fail "Unexpected stage remote."
git -C "$STAGE_DIR" pull --ff-only origin stage
cd "$STAGE_DIR"
export HAWATCH_STAGE_IMAGE_TAG="$(git rev-parse --short=12 HEAD)"
compose=(docker compose --project-name hawatch-stage --env-file "$STAGE_ENV" -f infra/compose/compose.stage.yaml)
# Validate without printing resolved production database credentials.
"${compose[@]}" config --quiet
attempt=0
until "${compose[@]}" build stage-api stage-web; do
  attempt=$((attempt + 1))
  [[ "$attempt" -lt "${DOCKER_BUILD_RETRIES:-2}" ]] || fail "Stage build failed; existing stage containers were retained."
  sleep 5
done
"${compose[@]}" up -d --no-build --force-recreate stage-api stage-web stage-gateway
for service in stage-api stage-web stage-gateway; do
  "${compose[@]}" ps --status running --services | grep -Fxq "$service" || \
    fail "Stage service $service did not reach running state; inspect compose logs."
done
stage_port="$(awk -F= '$1 == "HAWATCH_STAGE_PORT" {gsub(/[[:space:]\r]/, "", $2); print $2; exit}' "$STAGE_ENV")"
stage_port="${stage_port:-5050}"
ready=0
for attempt in {1..30}; do
  if curl --fail --silent --show-error --max-time 3 "http://127.0.0.1:${stage_port}/healthz" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
[[ "$ready" == "1" ]] || fail "Stage gateway on port ${stage_port} did not become healthy."
"${compose[@]}" ps

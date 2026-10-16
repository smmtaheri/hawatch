#!/usr/bin/env bash
set -Eeuo pipefail
# Runs on the server via SSH. Only existing, non-oneoff hawatch-stage containers
# are managed. No checkout/build/ingest, Compose down, pruning or volume deletion.
ACTION="${1:-status}"
STAGE_ENV="${2:-${HAWATCH_STAGE_ENV_FILE:-/root/hawatch-stage.env}}"
fail() { printf '[stage-hawatch] ERROR: %s\n' "$*" >&2; exit 1; }
[[ "$ACTION" == status || "$ACTION" == up || "$ACTION" == down ]] || fail 'Expected up, down or status.'
[[ "$STAGE_ENV" =~ ^/[A-Za-z0-9._/-]+$ && "$STAGE_ENV" != /root/hawatch/.env ]] || fail 'Invalid stage environment path.'
if [[ "$ACTION" != status ]]; then
  exec 9>"${STAGE_ENV}.lock"
  flock -n 9 || fail 'Another stage deploy/up/down is running.'
fi
services=(stage-postgres stage-redis stage-api stage-web stage-gateway stage-scheduler)
declare -A containers=() states=() healths=() images=()

load_state() {
  containers=(); states=(); healths=(); images=()
  local listing id details project service oneoff state health image
  local -a ids=()
  listing="$(docker ps -aq --filter label=com.docker.compose.project=hawatch-stage)"
  [[ -n "$listing" ]] || return 0
  while IFS= read -r id; do
    [[ -n "$id" ]] || continue
    [[ "$id" =~ ^[a-f0-9]{12,64}$ ]] || fail 'Unexpected container ID.'
    ids+=("$id")
  done <<< "$listing"
  details="$(docker inspect --format '{{.Id}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{index .Config.Labels "com.docker.compose.oneoff"}}|{{.State.Status}}|{{with index .State "Health"}}{{.Status}}{{else}}none{{end}}|{{.Config.Image}}' "${ids[@]}")"
  while IFS='|' read -r id project service oneoff state health image; do
    [[ "$id" =~ ^[a-f0-9]{12,64}$ ]] || fail 'Unexpected inspected container ID.'
    [[ "$project" == hawatch-stage ]] || fail 'Refusing a container outside hawatch-stage.'
    [[ "${oneoff,,}" != true ]] || continue
    case "$service" in
      stage-postgres|stage-redis|stage-api|stage-web|stage-gateway|stage-scheduler) ;;
      *) fail "Unexpected stage service: $service. Nothing was changed." ;;
    esac
    [[ -z "${containers[$service]:-}" ]] || fail "Duplicate container for $service. Nothing was changed."
    containers[$service]="$id"; states[$service]="$state"; healths[$service]="$health"; images[$service]="$image"
  done <<< "$details"
}

env_value() {
  [[ -f "$STAGE_ENV" ]] || return 0
  awk -F= -v key="$1" '$1 == key {sub(/^[^=]*=/, ""); sub(/\r$/, ""); print; exit}' "$STAGE_ENV"
}
read -ra connection <<< "${SSH_CONNECTION:-}"
origin="$(env_value HAWATCH_STAGE_ORIGIN)"
origin="${origin:-http://${connection[2]:-127.0.0.1}:5050}"
probe_host="$(env_value HAWATCH_STAGE_BIND_IP)"
case "${probe_host:-0.0.0.0}" in
  0.0.0.0|127.0.0.1) probe_host=127.0.0.1 ;;
esac
[[ "$probe_host" =~ ^[A-Za-z0-9.:-]+$ ]] || fail 'Invalid stage bind IP.'
probe="http://${probe_host}:5050"

healthy() {
  [[ "${states[$1]:-}" == running && ( "${healths[$1]:-}" == healthy || "${healths[$1]:-}" == none ) ]]
}
http_ready() {
  curl --fail --silent --max-time 3 "$probe/healthz" >/dev/null 2>&1 &&
    curl --fail --silent --max-time 3 "$probe/api/v1/health/ready/" >/dev/null 2>&1
}
report() {
  load_state
  local service present=0 running=0 ready=0
  for service in "${services[@]}"; do
    [[ -z "${containers[$service]:-}" ]] || present=$((present+1))
    [[ "${states[$service]:-}" != running ]] || running=$((running+1))
    if healthy "$service"; then ready=$((ready+1)); fi
  done
  if [[ "$present" == 0 ]]; then
    printf '[stage-hawatch] NOT DEPLOYED — run deploy-stage-hawatch first.\n'
  elif [[ "$running" == 0 ]]; then
    printf '[stage-hawatch] DOWN — containers and database are retained.\n'
  elif [[ "$ready" == 6 ]] && http_ready; then
    printf '[stage-hawatch] UP — all six services and HTTP/API readiness passed.\n'
  elif [[ "$running" == 6 ]]; then
    printf '[stage-hawatch] UNHEALTHY — services are running but health/readiness is incomplete.\n'
  else
    printf '[stage-hawatch] PARTIAL — some services are stopped or missing.\n'
  fi
  printf '%-18s %-12s %-12s %s\n' SERVICE STATE HEALTH IMAGE
  for service in "${services[@]}"; do
    printf '%-18s %-12s %-12s %s\n' "$service" "${states[$service]:-missing}" "${healths[$service]:-—}" "${images[$service]:-—}"
  done
  printf '[stage-hawatch] View after UP: %s/points/tochal\n' "${origin%/}"
}

load_state
case "$ACTION" in
  status) report; exit 0 ;;
  down)
    # Stop applications before their data services, retaining every container.
    for service in stage-scheduler stage-gateway stage-web stage-api stage-redis stage-postgres; do
      if [[ -n "${containers[$service]:-}" && "${states[$service]}" != exited && "${states[$service]}" != created ]]; then
        docker stop --time 30 "${containers[$service]}" >/dev/null
      fi
    done
    report ;;
  up)
    for service in "${services[@]}"; do
      [[ -n "${containers[$service]:-}" ]] || fail "Missing $service; run deploy-stage-hawatch first."
      [[ "${states[$service]}" != paused ]] || fail "$service is paused; inspect it before starting stage."
    done
    wait_seconds="${HAWATCH_STAGE_WAIT_SECONDS:-120}"
    [[ "$wait_seconds" =~ ^[0-9]{1,3}$ ]] || fail 'Invalid stage health timeout.'
    wait_seconds=$((10#$wait_seconds))
    [[ "$wait_seconds" -gt 0 && "$wait_seconds" -le 300 ]] || fail 'Invalid stage health timeout.'
    deadline=$((SECONDS+wait_seconds))
    for service in "${services[@]}"; do
      printf '[stage-hawatch] Starting %s\n' "$service"
      docker start "${containers[$service]}" >/dev/null
      while true; do
        load_state
        if healthy "$service"; then break; fi
        [[ $SECONDS -lt $deadline ]] || fail "$service did not become healthy; run stage-hawatch status."
        sleep 2
      done
    done
    http_ready || fail 'Services started but stage HTTP/API is not ready; run stage-hawatch status.'
    report ;;
esac

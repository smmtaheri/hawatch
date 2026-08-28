#!/usr/bin/env bash
set -Eeuo pipefail

# Bootstrap and deploy the lightweight Hawatch pilot stack.
#
# The script is intentionally scoped to one checkout and one Compose project:
# it never runs `docker compose down -v`, removes files, changes firewall rules,
# or enables the optional observability/cache profiles by default.

readonly DEFAULT_REPO_URL="https://github.com/smmtaheri/hawatch.git"
readonly DEFAULT_BRANCH="main"
readonly DEFAULT_DIR="/root/hawatch"
readonly COMPOSE_RELATIVE_PATH="infra/compose/compose.yaml"

REPO_URL="${HAWATCH_REPO_URL:-$DEFAULT_REPO_URL}"
BRANCH="${HAWATCH_BRANCH:-$DEFAULT_BRANCH}"
REPO_DIR="${HAWATCH_DIR:-$DEFAULT_DIR}"
RUN_INITIAL_INGEST="${RUN_INITIAL_INGEST:-1}"
ENABLE_OBSERVABILITY="${ENABLE_OBSERVABILITY:-0}"

log() {
  printf '[hawatch] %s\n' "$*"
}

fail() {
  printf '[hawatch] ERROR: %s\n' "$*" >&2
  exit 1
}

on_error() {
  local line_number="$1"
  printf '[hawatch] ERROR: command failed at line %s\n' "$line_number" >&2
}

trap 'on_error "$LINENO"' ERR

usage() {
  cat <<'EOF'
Usage:
  PUBLIC_HOST=<ip-or-domain> scripts/deploy.sh

Optional environment variables:
  HAWATCH_REPO_URL       Git URL (default: https://github.com/smmtaheri/hawatch.git)
  HAWATCH_BRANCH         Git branch (default: main)
  HAWATCH_DIR            Checkout directory (default: /root/hawatch)
  VITE_API_BASE_URL      Browser API URL (default: http://PUBLIC_HOST:8000/api/v1)
  API_PUBLISH_PORT       API host port (default: 8000)
  WEB_PUBLISH_PORT       Direct web host port (default: 5173)
  NGINX_PUBLISH_PORT     Gateway host port (default: 80)
  RUN_INITIAL_INGEST     Set 0 to skip the first live ingest
  ENABLE_OBSERVABILITY   Set 1 only on a host sized for the heavy stack

The script must run as root. It creates .env only when it does not exist.
Existing .env files are never replaced; existing secret values are preserved.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

[[ "$(uname -s)" == "Linux" ]] || fail "This deployment script supports Linux servers only."
[[ "${EUID}" -eq 0 ]] || fail "Run as root, or set HAWATCH_DIR and adapt the package installation for a non-root user."

install_base_packages() {
  local package_manager=""
  local -a packages=()

  [[ -s /etc/ssl/certs/ca-certificates.crt ]] || packages+=(ca-certificates)
  command -v curl >/dev/null 2>&1 || packages+=(curl)
  command -v git >/dev/null 2>&1 || packages+=(git)
  command -v openssl >/dev/null 2>&1 || packages+=(openssl)

  if [[ "${#packages[@]}" -eq 0 ]]; then
    return
  fi

  if command -v apt-get >/dev/null 2>&1; then
    package_manager="apt"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y ca-certificates "${packages[@]}"
  elif command -v dnf >/dev/null 2>&1; then
    package_manager="dnf"
    dnf install -y ca-certificates "${packages[@]}"
  elif command -v yum >/dev/null 2>&1; then
    package_manager="yum"
    yum install -y ca-certificates "${packages[@]}"
  elif command -v apk >/dev/null 2>&1; then
    package_manager="apk"
    apk add --no-cache ca-certificates curl git openssl
  else
    fail "No supported package manager found; install ca-certificates, curl, git and openssl first."
  fi

  log "Installed base packages with ${package_manager}."
}

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    log "Docker is missing; installing Docker Engine and the Compose plugin."
    curl -fsSL https://get.docker.com | sh
  fi

  if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files docker.service >/dev/null 2>&1; then
    systemctl enable --now docker
  elif command -v service >/dev/null 2>&1; then
    service docker start >/dev/null 2>&1 || true
  fi

  docker info >/dev/null 2>&1 || fail "Docker daemon is not reachable. Start Docker and run this script again."
  if ! docker compose version >/dev/null 2>&1; then
    log "Docker Compose v2 plugin is missing; installing it."
    if command -v apt-get >/dev/null 2>&1; then
      export DEBIAN_FRONTEND=noninteractive
      apt-get update
      apt-get install -y docker-compose-plugin
    elif command -v dnf >/dev/null 2>&1; then
      dnf install -y docker-compose-plugin
    elif command -v yum >/dev/null 2>&1; then
      yum install -y docker-compose-plugin
    elif command -v apk >/dev/null 2>&1; then
      apk add --no-cache docker-cli-compose
    fi
  fi
  docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 plugin is missing; install docker-compose-plugin and retry."
}

get_env_value() {
  local key="$1"
  awk -F= -v wanted_key="$key" '$1 == wanted_key {sub(/^[^=]*=/, ""); print; exit}' "$ENV_FILE"
}

set_env_value() {
  local key="$1"
  local value="$2"

  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >>"$ENV_FILE"
  fi
}

append_csv_value() {
  local current="$1"
  local value="$2"
  case ",${current}," in
    *,"${value}",*) printf '%s' "$current" ;;
    *)
      if [[ -n "$current" ]]; then
        printf '%s,%s' "$current" "$value"
      else
        printf '%s' "$value"
      fi
      ;;
  esac
}

random_hex() {
  openssl rand -hex 48
}

validate_secret() {
  local key="$1"
  local value
  value="$(get_env_value "$key")"
  [[ -n "$value" ]] || fail "$ENV_FILE is missing ${key}. Add a strong value and retry."
  [[ "$value" != replace-with-* ]] || fail "$ENV_FILE still contains the placeholder for ${key}."
}

configure_env() {
  ENV_FILE="$REPO_DIR/.env"
  if [[ ! -f "$ENV_FILE" ]]; then
    cp "$REPO_DIR/.env.example" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    set_env_value DJANGO_SECRET_KEY "$(random_hex)"
    set_env_value POSTGRES_PASSWORD "$(random_hex)"
    set_env_value HAWATCH_METRICS_TOKEN "$(random_hex)"
    set_env_value OPENSEARCH_INITIAL_ADMIN_PASSWORD "$(random_hex)"
    set_env_value OPENSEARCH_DASHBOARDS_SERVICE_PASSWORD "$(random_hex)"
    set_env_value GRAFANA_ADMIN_PASSWORD "$(random_hex)"
    log "Created $ENV_FILE with generated secrets (not printed)."
  else
    chmod 600 "$ENV_FILE"
    log "Using existing $ENV_FILE without overwriting it."
  fi

  [[ -n "${PUBLIC_HOST:-}" ]] || PUBLIC_HOST="$(hostname -I 2>/dev/null | awk '{print $1}')"
  [[ -n "${PUBLIC_HOST:-}" ]] || fail "Set PUBLIC_HOST to the server IP or domain (without http://)."
  [[ "$PUBLIC_HOST" != *"://"* && "$PUBLIC_HOST" != */* && "$PUBLIC_HOST" != *' '* ]] || \
    fail "PUBLIC_HOST must be a bare IP address or hostname, without scheme, path or spaces."

  API_PUBLISH_PORT="${API_PUBLISH_PORT:-$(get_env_value API_PUBLISH_PORT)}"
  WEB_PUBLISH_PORT="${WEB_PUBLISH_PORT:-$(get_env_value WEB_PUBLISH_PORT)}"
  NGINX_PUBLISH_PORT="${NGINX_PUBLISH_PORT:-$(get_env_value NGINX_PUBLISH_PORT)}"
  API_PUBLISH_PORT="${API_PUBLISH_PORT:-8000}"
  WEB_PUBLISH_PORT="${WEB_PUBLISH_PORT:-5173}"
  NGINX_PUBLISH_PORT="${NGINX_PUBLISH_PORT:-80}"

  VITE_API_BASE_URL="${VITE_API_BASE_URL:-$(get_env_value VITE_API_BASE_URL)}"
  if [[ -z "$VITE_API_BASE_URL" || "$VITE_API_BASE_URL" == "http://localhost:8000/api/v1" ]]; then
    VITE_API_BASE_URL="http://${PUBLIC_HOST}:${API_PUBLISH_PORT}/api/v1"
  fi

  set_env_value DJANGO_SETTINGS_MODULE "${DJANGO_SETTINGS_MODULE:-hawatch.config.settings.production}"
  set_env_value DJANGO_DEBUG false
  set_env_value DEMO_DATA_ENABLED false
  set_env_value HAWATCH_ENVIRONMENT production
  set_env_value POSTGRES_HOST postgres
  set_env_value POSTGRES_PORT 5432
  set_env_value API_PUBLISH_PORT "$API_PUBLISH_PORT"
  set_env_value WEB_PUBLISH_PORT "$WEB_PUBLISH_PORT"
  set_env_value NGINX_PUBLISH_PORT "$NGINX_PUBLISH_PORT"
  set_env_value VITE_API_BASE_URL "$VITE_API_BASE_URL"
  configured_hosts="${DJANGO_ALLOWED_HOSTS:-$(get_env_value DJANGO_ALLOWED_HOSTS)}"
  configured_hosts="${configured_hosts:-localhost,127.0.0.1,api,nginx}"
  configured_hosts="$(append_csv_value "$configured_hosts" "$PUBLIC_HOST")"
  configured_cors="${DJANGO_CORS_ALLOWED_ORIGINS:-$(get_env_value DJANGO_CORS_ALLOWED_ORIGINS)}"
  configured_cors="${configured_cors:-http://${PUBLIC_HOST}:${NGINX_PUBLISH_PORT},http://${PUBLIC_HOST}:${WEB_PUBLISH_PORT}}"
  configured_cors="$(append_csv_value "$configured_cors" "http://${PUBLIC_HOST}")"
  configured_cors="$(append_csv_value "$configured_cors" "https://${PUBLIC_HOST}")"
  set_env_value DJANGO_ALLOWED_HOSTS "$configured_hosts"
  set_env_value DJANGO_CORS_ALLOWED_ORIGINS "$configured_cors"

  validate_secret DJANGO_SECRET_KEY
  validate_secret POSTGRES_PASSWORD
  validate_secret HAWATCH_METRICS_TOKEN
  validate_secret OPENSEARCH_INITIAL_ADMIN_PASSWORD
  validate_secret OPENSEARCH_DASHBOARDS_SERVICE_PASSWORD
  validate_secret GRAFANA_ADMIN_PASSWORD
}

is_expected_remote() {
  case "$1" in
    https://github.com/smmtaheri/hawatch.git|git@github.com:smmtaheri/hawatch.git|ssh://git@github.com/smmtaheri/hawatch.git)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

checkout_repository() {
  if [[ -e "$REPO_DIR" && ! -d "$REPO_DIR" ]]; then
    fail "$REPO_DIR exists but is not a directory. Nothing was changed."
  fi

  if [[ -d "$REPO_DIR/.git" ]]; then
    local current_remote
    current_remote="$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || true)"
    is_expected_remote "$current_remote" || fail "Existing checkout has an unexpected origin: $current_remote"
    [[ -z "$(git -C "$REPO_DIR" status --porcelain)" ]] || fail "Existing checkout has local changes; commit or stash them first."
    git -C "$REPO_DIR" fetch --prune origin "$BRANCH"
    git -C "$REPO_DIR" checkout "$BRANCH"
    git -C "$REPO_DIR" pull --ff-only origin "$BRANCH"
    return
  fi

  if [[ -d "$REPO_DIR" && -n "$(find "$REPO_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    fail "$REPO_DIR is non-empty and is not a Hawatch git checkout. Nothing was changed."
  fi

  mkdir -p "$(dirname "$REPO_DIR")"
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$REPO_DIR"
}

wait_for_healthy() {
  local service="$1"
  local container_id=""
  local health_status=""

  for _ in $(seq 1 60); do
    container_id="$(docker compose --env-file "$ENV_FILE" -f "$REPO_DIR/$COMPOSE_RELATIVE_PATH" ps -q "$service" 2>/dev/null || true)"
    if [[ -n "$container_id" ]]; then
      health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || true)"
      case "$health_status" in
        healthy) return 0 ;;
        unhealthy)
          docker compose --env-file "$ENV_FILE" -f "$REPO_DIR/$COMPOSE_RELATIVE_PATH" logs --tail=80 "$service" >&2 || true
          fail "$service became unhealthy."
          ;;
      esac
    fi
    sleep 2
  done

  docker compose --env-file "$ENV_FILE" -f "$REPO_DIR/$COMPOSE_RELATIVE_PATH" logs --tail=80 "$service" >&2 || true
  fail "Timed out waiting for $service to become healthy."
}

wait_for_running() {
  local service="$1"
  local container_id=""
  local state=""

  for _ in $(seq 1 30); do
    container_id="$(docker compose --env-file "$ENV_FILE" -f "$REPO_DIR/$COMPOSE_RELATIVE_PATH" ps -q "$service" 2>/dev/null || true)"
    if [[ -n "$container_id" ]]; then
      state="$(docker inspect --format '{{.State.Status}}' "$container_id" 2>/dev/null || true)"
      [[ "$state" == running ]] && return 0
    fi
    sleep 2
  done
  fail "$service is not running."
}

run_stack() {
  local compose_file="$REPO_DIR/$COMPOSE_RELATIVE_PATH"
  local -a compose=(docker compose --env-file "$ENV_FILE" -f "$compose_file")
  if [[ "$ENABLE_OBSERVABILITY" == "1" ]]; then
    compose+=(--profile observability)
    log "Observability profile enabled by request. This needs materially more RAM and disk."
  else
    log "Starting the lightweight profile; Redis and observability remain stopped."
  fi

  "${compose[@]}" config --quiet
  if [[ "$ENABLE_OBSERVABILITY" == "1" ]]; then
    # Keep the one-shot ingest explicit so it runs exactly once below.
    "${compose[@]}" up -d --build postgres api web maintenance \
      opensearch opensearch-dashboards opensearch-auth-init opensearch-provisioner \
      vector prometheus grafana
  else
    "${compose[@]}" up -d --build postgres api web maintenance
  fi

  wait_for_healthy postgres
  wait_for_healthy api
  wait_for_healthy web
  wait_for_running maintenance

  # Nginx resolves Docker service names when it starts. Recreate the gateway
  # after API/Web replacement so it cannot retain a stale container IP.
  "${compose[@]}" up -d --force-recreate nginx
  wait_for_healthy nginx

  curl -fsS "http://127.0.0.1:${API_PUBLISH_PORT}/api/v1/health/ready/" >/dev/null
  curl -fsS "http://127.0.0.1:${NGINX_PUBLISH_PORT}/healthz" >/dev/null
  curl -fsS "http://127.0.0.1:${NGINX_PUBLISH_PORT}/" >/dev/null
  curl -fsS "http://127.0.0.1:${NGINX_PUBLISH_PORT}/api/v1/destinations/" >/dev/null
  curl -fsS "http://127.0.0.1:${NGINX_PUBLISH_PORT}/api/v1/destinations/touchal/" >/dev/null
  curl -fsS "http://127.0.0.1:${NGINX_PUBLISH_PORT}/api/v1/destinations/touchal/forecast/" >/dev/null
  curl -fsS "http://127.0.0.1:${NGINX_PUBLISH_PORT}/api/v1/routes/touchal-darband/" >/dev/null
  curl -fsS "http://127.0.0.1:${NGINX_PUBLISH_PORT}/api/v1/routes/touchal-darband/forecast/" >/dev/null

  if [[ "$RUN_INITIAL_INGEST" == "1" ]]; then
    log "Running one initial live ingest. Set RUN_INITIAL_INGEST=0 to skip it."
    "${compose[@]}" run --rm ingest
  else
    log "Initial ingest skipped (RUN_INITIAL_INGEST=${RUN_INITIAL_INGEST})."
  fi

  local metrics_token
  metrics_token="$(get_env_value HAWATCH_METRICS_TOKEN)"
  log "Operational status:"
  curl -fsS -H "Authorization: Bearer ${metrics_token}" \
    "http://127.0.0.1:${API_PUBLISH_PORT}/api/v1/health/status/"
  printf '\n'

  "${compose[@]}" ps
  cat <<EOF

Hawatch is running.
Frontend: http://${PUBLIC_HOST}:${NGINX_PUBLISH_PORT}
Frontend (direct): http://${PUBLIC_HOST}:${WEB_PUBLISH_PORT}
API: http://${PUBLIC_HOST}:${API_PUBLISH_PORT}/api/v1/
Ready: http://${PUBLIC_HOST}:${API_PUBLISH_PORT}/api/v1/health/ready/
Status: http://${PUBLIC_HOST}:${API_PUBLISH_PORT}/api/v1/health/status/ (Bearer token from .env)

Stop this Hawatch Compose project:
  cd ${REPO_DIR} && docker compose --env-file .env -f ${COMPOSE_RELATIVE_PATH} down
EOF
}

install_base_packages
ensure_docker
checkout_repository
configure_env
run_stack

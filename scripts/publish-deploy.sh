#!/usr/bin/env bash
set -Eeuo pipefail

# Push committed local work and deploy only the Hawatch checkout.
# This script never stages, commits, deletes, or changes uncommitted files.

readonly DEFAULT_REPO_DIR="/home/nobitex/Desktop/Tasks/Nobitex/hawatch"
readonly DEFAULT_BRANCH="main"
readonly DEFAULT_REMOTE="origin"
readonly DEFAULT_SSH_HOST="hawatch"
readonly DEFAULT_SERVER_DIR="/root/hawatch"
readonly DEFAULT_PUBLIC_HOST="hawatch.ir"
readonly DEFAULT_SERVER_IP="202.133.89.120"

REPO_DIR="${HAWATCH_LOCAL_DIR:-$DEFAULT_REPO_DIR}"
BRANCH="${HAWATCH_BRANCH:-$DEFAULT_BRANCH}"
REMOTE="${HAWATCH_REMOTE:-$DEFAULT_REMOTE}"
SSH_HOST="${HAWATCH_SSH_HOST:-$DEFAULT_SSH_HOST}"
SERVER_DIR="${HAWATCH_SERVER_DIR:-$DEFAULT_SERVER_DIR}"

env_value() {
  local key="$1"
  [[ -f "$REPO_DIR/.env" ]] || return 0
  awk -F= -v wanted_key="$key" '$1 == wanted_key {sub(/^[^=]*=/, ""); print; exit}' "$REPO_DIR/.env"
}

PUBLIC_HOST="${HAWATCH_PUBLIC_HOST:-${PUBLIC_HOST:-$(env_value PUBLIC_HOST)}}"
SERVER_IP="${HAWATCH_SERVER_IP:-$(env_value HAWATCH_SERVER_IP)}"
PUBLIC_HOST="${PUBLIC_HOST:-$DEFAULT_PUBLIC_HOST}"
SERVER_IP="${SERVER_IP:-$DEFAULT_SERVER_IP}"
SERVER_API_URL="${HAWATCH_SERVER_API_URL:-http://${SERVER_IP}:8000/api/v1}"

fail() {
  printf '[hawatch-publish] ERROR: %s\n' "$*" >&2
  exit 1
}

[[ -d "$REPO_DIR/.git" ]] || fail "Local Hawatch checkout not found: $REPO_DIR"
[[ "$(git -C "$REPO_DIR" branch --show-current)" == "$BRANCH" ]] || fail "Local branch must be $BRANCH"
[[ "$(git -C "$REPO_DIR" remote get-url "$REMOTE" 2>/dev/null || true)" == "git@github.com:smmtaheri/hawatch.git" ]] || \
  fail "Unexpected Git remote; refusing to deploy."
[[ "$PUBLIC_HOST" =~ ^[A-Za-z0-9.-]+$ ]] || fail "Invalid public host: $PUBLIC_HOST"
[[ "$SERVER_IP" =~ ^[A-Za-z0-9.-]+$ ]] || fail "Invalid server host: $SERVER_IP"
[[ "$SERVER_API_URL" =~ ^https?://[A-Za-z0-9.-]+:[0-9]+/api/v1$ ]] || fail "Invalid server API URL: $SERVER_API_URL"
[[ "$SERVER_DIR" =~ ^/[A-Za-z0-9._/-]+$ ]] || fail "Invalid server directory: $SERVER_DIR"

if [[ -n "$(git -C "$REPO_DIR" status --porcelain)" ]]; then
  printf '[hawatch-publish] WARNING: uncommitted local changes will not be staged, committed, or pushed.\n' >&2
fi

printf '[hawatch-publish] Pushing committed %s to %s...\n' "$BRANCH" "$REMOTE"
git -C "$REPO_DIR" push "$REMOTE" "$BRANCH"

printf '[hawatch-publish] Pulling and deploying on %s...\n' "$SSH_HOST"
ssh "$SSH_HOST" \
  "cd '$SERVER_DIR' && \
   git pull --ff-only '$REMOTE' '$BRANCH' && \
   PUBLIC_HOST='$PUBLIC_HOST' \
   VITE_API_BASE_URL='$SERVER_API_URL' \
   DJANGO_ALLOWED_HOSTS='$PUBLIC_HOST,www.$PUBLIC_HOST,$SERVER_IP,localhost,127.0.0.1,api,nginx' \
   DJANGO_CORS_ALLOWED_ORIGINS='http://$PUBLIC_HOST,https://$PUBLIC_HOST,http://www.$PUBLIC_HOST,https://www.$PUBLIC_HOST,http://$SERVER_IP,http://$SERVER_IP:5173' \
   RUN_INITIAL_INGEST=1 ./scripts/deploy.sh"

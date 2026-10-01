#!/usr/bin/env bash
set -Eeuo pipefail
# Disable stage persistently, then remove only this stack and legacy stage
# resources. Production's Compose project and external database network stay.
STAGE_ENV="${HAWATCH_STAGE_ENV_FILE:-/root/hawatch-stage.env}"
[[ -f "$STAGE_ENV" ]] || { printf '[hawatch-stage] ERROR: Missing %s\n' "$STAGE_ENV" >&2; exit 1; }
temporary_env="$(mktemp "${STAGE_ENV}.XXXXXX")"
trap 'rm -f "$temporary_env"' EXIT
awk '
  BEGIN { replaced = 0 }
  /^HAWATCH_STAGE_ENABLED=/ {
    if (!replaced) print "HAWATCH_STAGE_ENABLED=0"
    replaced = 1
    next
  }
  { print }
  END { if (!replaced) print "HAWATCH_STAGE_ENABLED=0" }
' "$STAGE_ENV" >"$temporary_env"
chmod --reference="$STAGE_ENV" "$temporary_env"
mv "$temporary_env" "$STAGE_ENV"
trap - EXIT

remove_project() {
  local project="$1" ids reference
  ids="$(docker ps -aq --filter "label=com.docker.compose.project=${project}")"
  [[ -z "$ids" ]] || docker rm -f $ids >/dev/null
  ids="$(docker network ls -q --filter "label=com.docker.compose.project=${project}")"
  [[ -z "$ids" ]] || docker network rm $ids >/dev/null 2>&1 || true
  ids="$(docker volume ls -q --filter "label=com.docker.compose.project=${project}")"
  [[ -z "$ids" ]] || docker volume rm $ids >/dev/null 2>&1 || true
  while IFS= read -r reference; do
    [[ -z "$reference" ]] || docker image rm "$reference" >/dev/null 2>&1 || true
  done < <(docker image ls --format '{{.Repository}}:{{.Tag}}' | awk -F: -v prefix="$project" '$1 == prefix "-api" || $1 == prefix "-web" {print $0}')
}

remove_project hawatch-stage
remove_project hawatch-new-design
printf '[hawatch-stage] Disabled; stage containers, networks, log volumes and local images are removed.\n'

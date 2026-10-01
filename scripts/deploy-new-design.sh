#!/usr/bin/env bash
set -Eeuo pipefail
# Operator-run QA deployment only. Never invoke the production entrypoint.
QA_DIR="${HAWATCH_QA_DIR:-/root/hawatch-new-design}"
QA_ENV="${HAWATCH_QA_ENV_FILE:-/root/hawatch-new-design.qa.env}"
fail() { printf '[hawatch-qa] %s\n' "$*" >&2; exit 1; }
[[ -d "$QA_DIR" && -f "$QA_ENV" ]] || fail "Prepare QA checkout and QA environment file first."
[[ "$(git -C "$QA_DIR" branch --show-current)" == new-design ]] || fail "QA checkout must be on new-design."
[[ -z "$(git -C "$QA_DIR" status --porcelain)" ]] || fail "QA checkout contains uncommitted changes; nothing was reset."
[[ "$(git -C "$QA_DIR" remote get-url origin)" =~ ^(git@github.com:smmtaheri/hawatch.git|https://github.com/smmtaheri/hawatch.git)$ ]] || fail "Unexpected QA remote."
git -C "$QA_DIR" pull --ff-only origin new-design
cd "$QA_DIR"
export HAWATCH_QA_IMAGE_TAG="$(git rev-parse --short=12 HEAD)"
compose=(docker compose --project-name hawatch-new-design --env-file "$QA_ENV" -f infra/compose/compose.new-design.yaml)
# Validate without printing resolved database credentials.
"${compose[@]}" config --quiet
attempt=0
until "${compose[@]}" build qa-api qa-web; do
  attempt=$((attempt + 1))
  [[ "$attempt" -lt "${DOCKER_BUILD_RETRIES:-2}" ]] || fail "QA build failed; running QA containers were retained."
  sleep 5
done
"${compose[@]}" up -d --no-build --force-recreate qa-api qa-web qa-gateway
"${compose[@]}" ps

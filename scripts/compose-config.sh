#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
docker compose -f "$ROOT/infra/compose/compose.yaml" config >/dev/null
echo "compose config: ok"

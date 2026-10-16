#!/usr/bin/env bash
set -Eeuo pipefail
# Direct server entry point shares the same non-destructive implementation.
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
exec bash "$SCRIPT_DIR/control-stage.sh" down

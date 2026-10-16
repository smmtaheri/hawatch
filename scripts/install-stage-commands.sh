#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
CHECKOUT="$(dirname "$SCRIPT_DIR")"
BIN_DIR="${HAWATCH_COMMAND_BIN_DIR:-$HOME/.local/bin}"
fail() { printf '[stage-hawatch] ERROR: %s\n' "$*" >&2; exit 1; }
[[ "$(git -C "$CHECKOUT" branch --show-current)" == stage ]] || fail 'Install from the dedicated stage worktree.'
[[ "$(git -C "$CHECKOUT" remote get-url origin)" == git@github.com:smmtaheri/hawatch.git ]] || fail 'Unexpected stage remote.'
mkdir -p "$BIN_DIR"
for command in deploy-stage-hawatch stage-hawatch; do
  target="$BIN_DIR/$command"
  [[ -f "$SCRIPT_DIR/$command" ]] || fail "Missing $command."
  if [[ -e "$target" || -L "$target" ]]; then
    [[ -L "$target" ]] || fail "Will not overwrite a non-symlink: $target"
    previous="$(readlink -f "$target")"
    previous_checkout="$(dirname "$(dirname "$previous")")"
    [[ "${previous##*/}" == "$command" && "$(git -C "$previous_checkout" remote get-url origin 2>/dev/null || true)" == git@github.com:smmtaheri/hawatch.git ]] || fail "Unexpected existing command: $target"
  fi
done
for command in deploy-stage-hawatch stage-hawatch; do
  ln -sfn "$SCRIPT_DIR/$command" "$BIN_DIR/$command"
done
printf '[stage-hawatch] Installed in %s; current folder/branch does not select the release.\n' "$BIN_DIR"

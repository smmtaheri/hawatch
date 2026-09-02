#!/usr/bin/env python3
"""Validate and publish a database-first Hawatch catalog.

The catalog stays on the operator's machine and is sent to the API container
over SSH stdin. This script never copies a catalog or GPX file to the server,
never parses ``tracks/`` at runtime, and never changes application code.

Default mode is read-only. Use ``--apply`` only after the local provider check
and the remote ``seed_catalog --check-only`` both pass.

Example:
  python3 scripts/publish_catalog.py \
    --catalog /tmp/damavand_v1.json \
    --host root@203.0.113.10

  python3 scripts/publish_catalog.py \
    --catalog /tmp/damavand_v1.json \
    --host root@203.0.113.10 \
    --apply
"""

from __future__ import annotations

import argparse
import json
import posixpath
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


class WorkflowError(RuntimeError):
    """A workflow step failed."""


def _remote_path(remote_dir: str, value: str) -> str:
    if value.startswith("/"):
        return value
    return posixpath.join(remote_dir.rstrip("/"), value)


def remote_command(
    *,
    host: str,
    remote_dir: str,
    env_file: str,
    compose_file: str,
    manage_args: Sequence[str],
) -> list[str]:
    """Build an SSH argv without an unquoted shell fragment or ``cd`` chain."""
    compose_args = [
        "docker",
        "compose",
        "--project-directory",
        remote_dir,
        "--env-file",
        _remote_path(remote_dir, env_file),
        "-f",
        _remote_path(remote_dir, compose_file),
        "exec",
        "-T",
        "api",
        "python",
        "manage.py",
        *manage_args,
    ]
    return ["ssh", host, shlex.join(compose_args)]


def pending_timing_routes(catalog: dict[str, Any]) -> list[str]:
    """Return route slugs that cannot produce arrival-aware weather yet."""
    pending: list[str] = []
    for key, route in (catalog.get("routes") or {}).items():
        slug = str(route.get("slug") or key)
        status = route.get("timing_status", "pending")
        if status not in {"estimated", "curated"} or not route.get("timing"):
            pending.append(slug)
    return pending


def _run_step(label: str, argv: Sequence[str], *, input_bytes: bytes | None = None) -> None:
    print(f"[catalog] {label}")
    try:
        completed = subprocess.run(list(argv), input=input_bytes, check=False)
    except OSError as exc:
        raise WorkflowError(f"{label} could not start: {exc}") from exc
    if completed.returncode:
        suffix = "; no database changes were made" if "validation" in label.lower() else ""
        raise WorkflowError(f"{label} failed with exit code {completed.returncode}{suffix}")


def _local_validator_command(
    *, script_path: Path, catalog_path: Path, forecast_days: int, allow_unresolved_elevation: bool
) -> list[str]:
    command = [
        sys.executable,
        str(script_path),
        "--catalog",
        str(catalog_path),
        "--forecast-days",
        str(forecast_days),
    ]
    if allow_unresolved_elevation:
        command.append("--allow-unresolved-elevation")
    return command


def run_workflow(args: argparse.Namespace) -> None:
    catalog_path = args.catalog.expanduser().resolve()
    if not catalog_path.is_file():
        raise WorkflowError(f"catalog file does not exist: {catalog_path}")
    try:
        catalog_bytes = catalog_path.read_bytes()
        catalog = json.loads(catalog_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"catalog is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(catalog, dict):
        raise WorkflowError("catalog root must be a JSON object")

    if args.apply and args.skip_provider_validation:
        raise WorkflowError(
            "refusing --apply with --skip-provider-validation; provider/DEM validation is required before import"
        )
    if args.apply and args.allow_unresolved_elevation:
        raise WorkflowError(
            "refusing --apply with --allow-unresolved-elevation; every imported point needs a validated elevation"
        )

    destination = str(args.destination or (catalog.get("destination") or {}).get("slug") or "").strip()
    if not destination:
        raise WorkflowError("destination slug is missing; use --destination or catalog.destination.slug")
    point_slugs = [str(slug) for slug in (catalog.get("weather_points") or {})]
    if not point_slugs:
        raise WorkflowError("catalog.weather_points must contain at least one point")

    if not args.skip_provider_validation:
        script_path = Path(__file__).with_name("validate_open_meteo_catalog.py")
        _run_step(
            "local Open-Meteo/DEM validation",
            _local_validator_command(
                script_path=script_path,
                catalog_path=catalog_path,
                forecast_days=args.forecast_days,
                allow_unresolved_elevation=args.allow_unresolved_elevation,
            ),
        )
    else:
        print("[catalog] local provider validation skipped by explicit flag")

    remote_check = remote_command(
        host=args.host,
        remote_dir=args.remote_dir,
        env_file=args.env_file,
        compose_file=args.compose_file,
        manage_args=["seed_catalog", "--stdin", "--check-only"],
    )
    _run_step("remote catalog shape check (no database write)", remote_check, input_bytes=catalog_bytes)

    if not args.apply:
        print("[catalog] checks passed; no database changes were made (use --apply to publish)")
        return

    pending = pending_timing_routes(catalog)
    if pending and not args.allow_pending_timing:
        raise WorkflowError(
            "refusing to publish routes without arrival timing: "
            + ", ".join(pending)
            + "; add timing blocks or pass --allow-pending-timing deliberately"
        )

    remote_import = remote_command(
        host=args.host,
        remote_dir=args.remote_dir,
        env_file=args.env_file,
        compose_file=args.compose_file,
        manage_args=["seed_catalog", "--stdin", "--strict"],
    )
    _run_step("atomic catalog import", remote_import, input_bytes=catalog_bytes)

    ingest_args = ["ingest_open_meteo", "--slugs", ",".join(point_slugs)]
    remote_ingest = remote_command(
        host=args.host,
        remote_dir=args.remote_dir,
        env_file=args.env_file,
        compose_file=args.compose_file,
        manage_args=ingest_args,
    )
    _run_step("targeted Open-Meteo ingest", remote_ingest)

    preflight_args = ["catalog_preflight", "--destination", destination, "--require-forecast"]
    if not pending:
        preflight_args.append("--strict")
    remote_preflight = remote_command(
        host=args.host,
        remote_dir=args.remote_dir,
        env_file=args.env_file,
        compose_file=args.compose_file,
        manage_args=preflight_args,
    )
    _run_step("post-import database preflight", remote_preflight)
    print(f"[catalog] published {destination}; refresh the destination/route page to verify arrival weather")


def build_parser() -> argparse.ArgumentParser:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True, help="Local catalog JSON; it is sent over SSH stdin.")
    parser.add_argument("--host", required=True, help="SSH target, for example root@203.0.113.10.")
    parser.add_argument("--destination", default="", help="Destination slug; defaults to catalog.destination.slug.")
    parser.add_argument("--remote-dir", default="/root/hawatch")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--compose-file", default="infra/compose/compose.yaml")
    parser.add_argument("--forecast-days", type=int, default=1)
    parser.add_argument("--allow-unresolved-elevation", action="store_true")
    parser.add_argument(
        "--skip-provider-validation",
        action="store_true",
        help="Skip provider validation for a read-only draft check; cannot be combined with --apply.",
    )
    parser.add_argument(
        "--allow-pending-timing",
        action="store_true",
        help="Allow publishing routes that intentionally remain pending; their arrival weather stays unavailable.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the catalog, ingest forecasts and run post-import preflight. Default is read-only.",
    )
    parser.epilog = f"Repository root: {repo}"
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_workflow(args)
    except WorkflowError as exc:
        print(f"[catalog] ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

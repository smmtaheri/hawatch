#!/usr/bin/env python3
"""Production-like Open-Meteo collector for هواچ.

The runner intentionally uses one conservative forecast request shape:

* the real points from ``hawatch_route_points_catalog.json``;
* ``models=best_match`` and ``cell_selection=land``;
* the catalog elevation when it is available;
* ten hourly variables and a configurable forecast horizon.

It is designed for a small server and the Python standard library only.  It
supports a one-shot cycle, a long-running daemon, and a dry-run planner.
Successful batch files are written atomically.  ``latest.json`` is replaced
only after every eligible point in the cycle has a valid response.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import email.utils
import fcntl
import hashlib
import http.client
import json
import math
import os
import random
import signal
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


SCRIPT_VERSION = "1.0.0"
SCHEMA_VERSION = "hawatch.openmeteo.runner.v1"
API_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_TIMEZONE = "Asia/Tehran"
DEFAULT_MODEL = "best_match"
DEFAULT_CELL_SELECTION = "land"

# Keep this at ten variables for the free-tier pilot.  The Open-Meteo pricing
# page says requests with more than ten variables can count as multiple calls.
DEFAULT_HOURLY_VARIABLES = (
    "temperature_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "snowfall",
    "weather_code",
    "visibility",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
)

STOP_REQUESTED = threading.Event()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def run_id_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def is_finite_number(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_dump_atomic(path: Path, payload: Any, *, pretty: bool = True) -> None:
    """Write JSON in the same directory and replace the destination atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_name = stream.name
            json.dump(
                payload,
                stream,
                ensure_ascii=False,
                indent=2 if pretty else None,
                separators=None if pretty else (",", ":"),
                sort_keys=False,
                allow_nan=False,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary_name)


class JsonlLogger:
    """Small structured logger suitable for ``tail`` and ``jq``."""

    def __init__(self, log_path: Path, error_path: Path):
        self.log_path = log_path
        self.error_path = error_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.error_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def event(self, event: str, *, level: str = "INFO", error: bool = False, **fields: Any) -> None:
        record = {
            "ts_utc": utc_now(),
            "level": level,
            "event": event,
            **fields,
        }
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as stream:
                stream.write(line)
                stream.flush()
            if error or level in {"ERROR", "CRITICAL"}:
                with self.error_path.open("a", encoding="utf-8") as stream:
                    stream.write(line)
                    stream.flush()


class ProcessLock:
    """A kernel lock; unlike a hand-written PID file it is released on exit."""

    def __init__(self, path: Path):
        self.path = path
        self.stream: Any | None = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.stream.close()
            self.stream = None
            return False
        self.stream.seek(0)
        self.stream.truncate()
        self.stream.write(f"pid={os.getpid()} started_at_utc={utc_now()}\n")
        self.stream.flush()
        return True

    def release(self) -> None:
        if self.stream is None:
            return
        with contextlib.suppress(OSError):
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
        self.stream.close()
        self.stream = None

    def __enter__(self) -> "ProcessLock":
        if not self.acquire():
            raise RuntimeError(f"another هواچ weather cycle already holds {self.path}")
        return self

    def __exit__(self, *_: Any) -> None:
        self.release()


@dataclass(frozen=True)
class Config:
    catalog_path: Path
    data_dir: Path
    state_dir: Path
    logs_dir: Path
    batch_size: int = 100
    pause_seconds: float = 10.0
    timeout_seconds: float = 60.0
    max_retries: int = 3
    backoff_base_seconds: float = 2.0
    max_backoff_seconds: float = 120.0
    minutely_wait_seconds: float = 65.0
    forecast_hours: int = 72
    model: str = DEFAULT_MODEL
    cell_selection: str = DEFAULT_CELL_SELECTION
    timezone: str = DEFAULT_TIMEZONE
    interval_seconds: float = 4 * 60 * 60
    hourly_variables: tuple[str, ...] = DEFAULT_HOURLY_VARIABLES

    @property
    def latest_path(self) -> Path:
        return self.data_dir / "latest.json"

    @property
    def runs_dir(self) -> Path:
        return self.data_dir / "runs"

    @property
    def batches_dir(self) -> Path:
        return self.data_dir / "batches"

    @property
    def checkpoint_path(self) -> Path:
        return self.state_dir / "checkpoint.json"

    @property
    def lock_path(self) -> Path:
        return self.state_dir / "hawatch-weather.lock"

    @property
    def plan_fingerprint(self) -> str:
        plan = {
            "catalog_sha256": sha256_file(self.catalog_path),
            "batch_size": self.batch_size,
            "forecast_hours": self.forecast_hours,
            "model": self.model,
            "cell_selection": self.cell_selection,
            "timezone": self.timezone,
            "hourly_variables": list(self.hourly_variables),
        }
        return hashlib.sha256(
            json.dumps(plan, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    def public_dict(self) -> dict[str, Any]:
        return {
            "endpoint": API_URL,
            "batch_size": self.batch_size,
            "pause_seconds": self.pause_seconds,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "backoff_base_seconds": self.backoff_base_seconds,
            "max_backoff_seconds": self.max_backoff_seconds,
            "minutely_wait_seconds": self.minutely_wait_seconds,
            "forecast_hours": self.forecast_hours,
            "model": self.model,
            "cell_selection": self.cell_selection,
            "timezone": self.timezone,
            "hourly_variables": list(self.hourly_variables),
            "user_agent": f"hawatch-weather-runner/{SCRIPT_VERSION}",
        }


def load_catalog(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str]:
    if not path.exists():
        raise FileNotFoundError(f"catalog not found: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"catalog is not valid JSON: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("points"), list):
        raise ValueError("catalog must be an object with a points array")

    active: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(document["points"], start=1):
        if not isinstance(raw, dict):
            skipped.append({"index": index, "reason": "point_is_not_object"})
            continue
        point_id = str(raw.get("id", "")).strip()
        if not point_id:
            skipped.append({"index": index, "reason": "missing_id"})
            continue
        if point_id in seen_ids:
            raise ValueError(f"duplicate point id in catalog: {point_id}")
        seen_ids.add(point_id)

        enabled = raw.get("weather_sampling_enabled") is True
        if not enabled:
            skipped.append({"point_id": point_id, "reason": "weather_sampling_disabled"})
            continue
        if not is_finite_number(raw.get("latitude")) or not is_finite_number(raw.get("longitude")):
            skipped.append({"point_id": point_id, "reason": "invalid_coordinates"})
            continue

        point = dict(raw)
        point["id"] = point_id
        point["latitude"] = float(raw["latitude"])
        point["longitude"] = float(raw["longitude"])
        if raw.get("elevation_m") is not None and is_finite_number(raw.get("elevation_m")):
            point["elevation_m"] = float(raw["elevation_m"])
        else:
            point["elevation_m"] = None
        active.append(point)
    if not active:
        raise ValueError("catalog has no enabled points with valid coordinates")
    return document, active, skipped, sha256_file(path)


def chunked(items: Sequence[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [list(items[start : start + size]) for start in range(0, len(items), size)]


def planned_batches(items: Sequence[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    """Keep catalog elevations wherever possible without sending a mixed list."""
    with_elevation = [point for point in items if point.get("elevation_m") is not None]
    without_elevation = [point for point in items if point.get("elevation_m") is None]
    return chunked(with_elevation, size) + chunked(without_elevation, size)


def build_request_params(batch: Sequence[dict[str, Any]], config: Config) -> dict[str, str]:
    params: dict[str, str] = {
        "latitude": ",".join(f"{point['latitude']:.5f}" for point in batch),
        "longitude": ",".join(f"{point['longitude']:.5f}" for point in batch),
        "timezone": config.timezone,
        "models": config.model,
        "cell_selection": config.cell_selection,
        "forecast_hours": str(config.forecast_hours),
        "hourly": ",".join(config.hourly_variables),
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timeformat": "iso8601",
    }
    # If a batch has mixed missing elevations, omitting the parameter lets the
    # API use its documented DEM fallback for that batch instead of sending an
    # ambiguous partial list.
    if all(point.get("elevation_m") is not None for point in batch):
        params["elevation"] = ",".join(str(point["elevation_m"]) for point in batch)
    return params


def build_request_url(params: dict[str, str]) -> str:
    return f"{API_URL}?{urllib.parse.urlencode(params)}"


@dataclass
class RequestResult:
    status: int | None
    payload: Any
    elapsed_seconds: float
    error_kind: str | None = None
    error_message: str | None = None
    reason: str | None = None
    headers: dict[str, str] | None = None
    retry_after_seconds: float | None = None


def parse_retry_after(headers: dict[str, str]) -> float | None:
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, float(raw.strip()))
    except ValueError:
        try:
            target = email.utils.parsedate_to_datetime(raw)
            if target.tzinfo is None:
                target = target.replace(tzinfo=dt.timezone.utc)
            return max(0.0, (target - dt.datetime.now(dt.timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def parse_error_payload(body: str) -> tuple[Any, str | None]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return {"raw_error": body[:2000]}, body[:500] or None
    reason = payload.get("reason") if isinstance(payload, dict) else None
    return payload, str(reason) if reason is not None else None


def fetch_json(url: str, config: Config) -> RequestResult:
    started = time.monotonic()
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": f"hawatch-weather-runner/{SCRIPT_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            status = int(response.status)
            headers = dict(response.headers.items())
            body = response.read().decode("utf-8")
        elapsed = time.monotonic() - started
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            return RequestResult(
                status=status,
                payload=None,
                elapsed_seconds=elapsed,
                error_kind="json_decode_error",
                error_message=str(exc),
                headers=headers,
            )
        return RequestResult(status=status, payload=payload, elapsed_seconds=elapsed, headers=headers)
    except urllib.error.HTTPError as exc:
        headers = dict(exc.headers.items()) if exc.headers else {}
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except OSError:
            body = ""
        payload, reason = parse_error_payload(body)
        return RequestResult(
            status=int(exc.code),
            payload=payload,
            elapsed_seconds=time.monotonic() - started,
            error_kind="http_error",
            error_message=reason or str(exc),
            reason=reason,
            headers=headers,
            retry_after_seconds=parse_retry_after(headers),
        )
    except (urllib.error.URLError, TimeoutError, socket.timeout, socket.gaierror, ConnectionError, OSError, http.client.IncompleteRead) as exc:
        kind = "timeout" if isinstance(exc, (TimeoutError, socket.timeout)) else "network_error"
        return RequestResult(
            status=None,
            payload=None,
            elapsed_seconds=time.monotonic() - started,
            error_kind=kind,
            error_message=str(exc),
        )


def rate_limit_scope(result: RequestResult) -> str | None:
    if result.status != 429:
        return None
    text = " ".join(
        value for value in (result.reason, result.error_message) if value
    ).lower()
    for scope in ("minutely", "hourly", "daily", "monthly"):
        if scope in text:
            return scope
    return "unknown"


def as_location_list(payload: Any, expected_count: int) -> list[dict[str, Any]] | None:
    if expected_count == 1 and isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list) and len(payload) == expected_count and all(isinstance(x, dict) for x in payload):
        return payload
    return None


def validate_forecast_payload(
    payload: Any,
    batch: Sequence[dict[str, Any]],
    variables: Sequence[str],
) -> tuple[bool, str, list[dict[str, Any]] | None, list[str], list[str]]:
    records = as_location_list(payload, len(batch))
    if records is None:
        return False, "response_shape_or_point_count_mismatch", None, [], []

    empty_point_ids: list[str] = []
    invalid_point_ids: list[str] = []
    for point, record in zip(batch, records):
        hourly = record.get("hourly")
        if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
            invalid_point_ids.append(point["id"])
            continue
        times = hourly["time"]
        if not times:
            empty_point_ids.append(point["id"])
            continue
        expected_length = len(times)
        missing = [variable for variable in variables if variable not in hourly]
        wrong_length = [
            variable
            for variable in variables
            if not isinstance(hourly.get(variable), list)
            or len(hourly[variable]) != expected_length
        ]
        if missing or wrong_length:
            invalid_point_ids.append(point["id"])
    if invalid_point_ids:
        return False, "missing_or_misaligned_hourly_data", records, empty_point_ids, invalid_point_ids
    if empty_point_ids:
        return False, "empty_hourly_data", records, empty_point_ids, []
    return True, "ok", records, [], []


def interruptible_sleep(seconds: float) -> bool:
    """Return False when a shutdown was requested while sleeping."""
    return not STOP_REQUESTED.wait(max(0.0, seconds))


def backoff_seconds(config: Config, attempt_number: int) -> float:
    base = min(
        config.max_backoff_seconds,
        config.backoff_base_seconds * (2 ** max(0, attempt_number - 1)),
    )
    jitter = random.uniform(0.0, min(1.0, max(0.1, base * 0.1)))
    return base + jitter


def process_batch(
    batch: Sequence[dict[str, Any]],
    batch_number: int,
    config: Config,
    logger: JsonlLogger,
    run_id: str,
) -> dict[str, Any]:
    params = build_request_params(batch, config)
    url = build_request_url(params)
    attempts: list[dict[str, Any]] = []
    max_attempts = config.max_retries + 1
    final_records: list[dict[str, Any]] | None = None
    final_validation = "not_attempted"
    final_empty: list[str] = []
    final_invalid: list[str] = []
    final_result: RequestResult | None = None
    started_at = utc_now()

    for attempt_number in range(1, max_attempts + 1):
        if STOP_REQUESTED.is_set():
            final_validation = "shutdown_requested"
            break
        result = fetch_json(url, config)
        final_result = result
        scope = rate_limit_scope(result)
        attempt_outcome = "success" if result.status == 200 and result.error_kind is None else "failure"
        validation_message: str | None = None
        empty_ids: list[str] = []
        invalid_ids: list[str] = []
        records: list[dict[str, Any]] | None = None
        if result.status == 200 and result.error_kind is None:
            valid, validation_message, records, empty_ids, invalid_ids = validate_forecast_payload(
                result.payload, batch, config.hourly_variables
            )
            if not valid:
                attempt_outcome = "invalid_response"
            else:
                final_records = records
                final_validation = "ok"
        elif result.error_kind:
            validation_message = result.error_kind

        attempt_record = {
            "attempt": attempt_number,
            "http_status": result.status,
            "outcome": attempt_outcome,
            "error_kind": result.error_kind,
            "error_message": (result.error_message or "")[:500] or None,
            "reason": (result.reason or "")[:500] or None,
            "rate_limit_scope": scope,
            "retry_after_seconds": result.retry_after_seconds,
            "elapsed_seconds": round(result.elapsed_seconds, 3),
            "validation_message": validation_message,
        }
        attempts.append(attempt_record)
        logger.event(
            "batch_attempt",
            run_id=run_id,
            batch_number=batch_number,
            attempt=attempt_number,
            http_status=result.status,
            outcome=attempt_outcome,
            error_kind=result.error_kind,
            rate_limit_scope=scope,
            elapsed_seconds=round(result.elapsed_seconds, 3),
        )

        final_empty = empty_ids
        final_invalid = invalid_ids
        retryable = False
        wait_seconds: float | None = None
        if result.status == 200 and result.error_kind is None:
            retryable = not (final_validation == "ok")
            if retryable:
                wait_seconds = backoff_seconds(config, attempt_number)
        elif scope == "minutely":
            retryable = True
            wait_seconds = max(
                config.minutely_wait_seconds,
                result.retry_after_seconds or 0.0,
            )
        elif scope in {"hourly", "daily", "monthly", "unknown"}:
            retryable = False
        elif result.status is not None and 500 <= result.status <= 599:
            retryable = True
            wait_seconds = backoff_seconds(config, attempt_number)
        elif result.status in {408, 425}:
            retryable = True
            wait_seconds = backoff_seconds(config, attempt_number)
        elif result.error_kind in {"network_error", "timeout", "json_decode_error"}:
            retryable = True
            wait_seconds = backoff_seconds(config, attempt_number)

        if not retryable or attempt_number >= max_attempts:
            break
        logger.event(
            "retry_scheduled",
            run_id=run_id,
            batch_number=batch_number,
            attempt=attempt_number,
            next_attempt=attempt_number + 1,
            wait_seconds=round(wait_seconds or 0.0, 3),
            reason=scope or result.error_kind or validation_message or "retryable_failure",
        )
        if not interruptible_sleep(wait_seconds or 0.0):
            final_validation = "shutdown_requested"
            break

    finished_at = utc_now()
    success = final_validation == "ok" and final_records is not None and not STOP_REQUESTED.is_set()
    status = "success" if success else "failed"
    if STOP_REQUESTED.is_set() and final_validation != "ok":
        status = "shutdown"
    return {
        "schema_version": SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "run_id": run_id,
        "batch_number": batch_number,
        "status": status,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "requested_points": len(batch),
        "point_ids": [point["id"] for point in batch],
        "request": {
            "endpoint": API_URL,
            "params": params,
            "requested_model": config.model,
            "cell_selection": config.cell_selection,
            "elevation_source": "catalog" if "elevation" in params else "open_meteo_default_dem",
        },
        "attempts": attempts,
        "http_status": final_result.status if final_result else None,
        "elapsed_seconds": round(sum(item["elapsed_seconds"] for item in attempts), 3),
        "returned_points": len(final_records) if final_records is not None else 0,
        "validation": {
            "ok": success,
            "message": final_validation,
            "empty_point_ids": final_empty,
            "invalid_point_ids": final_invalid,
        },
        "data": final_records if success else None,
    }


def batch_path(config: Config, run_id: str, batch_number: int) -> Path:
    return config.batches_dir / run_id / f"batch-{batch_number:04d}.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_checkpoint(config: Config) -> dict[str, Any] | None:
    if not config.checkpoint_path.exists():
        return None
    try:
        checkpoint = read_json(config.checkpoint_path)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(checkpoint, dict):
        return None
    if checkpoint.get("status") not in {"running", "paused", "partial", "shutdown"}:
        return None
    if checkpoint.get("plan_fingerprint") != config.plan_fingerprint:
        return None
    return checkpoint


def new_checkpoint(
    config: Config,
    run_id: str,
    catalog: dict[str, Any],
    active_points: Sequence[dict[str, Any]],
    skipped_points: Sequence[dict[str, Any]],
    catalog_sha256: str,
    total_batches: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "status": "running",
        "run_id": run_id,
        "started_at_utc": utc_now(),
        "catalog_path": str(config.catalog_path.resolve()),
        "catalog_sha256": catalog_sha256,
        "catalog_schema_version": catalog.get("schema_version"),
        "plan_fingerprint": config.plan_fingerprint,
        "total_points": len(active_points),
        "point_ids": [point["id"] for point in active_points],
        "skipped_points": list(skipped_points),
        "total_batches": total_batches,
        "completed_batch_numbers": [],
        "config": config.public_dict(),
    }


def update_checkpoint(config: Config, checkpoint: dict[str, Any]) -> None:
    json_dump_atomic(config.checkpoint_path, checkpoint)


def load_successful_records(config: Config, run_id: str, batch_number: int) -> list[dict[str, Any]]:
    payload = read_json(batch_path(config, run_id, batch_number))
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise ValueError(f"batch {batch_number} is not a successful batch")
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError(f"batch {batch_number} has no data")
    return data


def collect_batch_records(
    config: Config,
    run_id: str,
    active_points: Sequence[dict[str, Any]],
    total_batches: int,
) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    batches = planned_batches(active_points, config.batch_size)
    for batch_number in range(1, total_batches + 1):
        data = load_successful_records(config, run_id, batch_number)
        for point, record in zip(batches[batch_number - 1], data):
            records[point["id"]] = record
    return records


def build_latest(
    config: Config,
    run_id: str,
    catalog: dict[str, Any],
    active_points: Sequence[dict[str, Any]],
    skipped_points: Sequence[dict[str, Any]],
    catalog_sha256: str,
    started_at_utc: str,
) -> dict[str, Any]:
    records = collect_batch_records(config, run_id, active_points, len(planned_batches(active_points, config.batch_size)))
    point_payloads: list[dict[str, Any]] = []
    model_versions: set[str] = set()
    for point in active_points:
        record = records[point["id"]]
        for field in ("model", "model_version", "model_run"):
            if record.get(field) is not None:
                model_versions.add(str(record[field]))
        point_payloads.append(
            {
                "id": point["id"],
                "name_fa": point.get("name_fa"),
                "name_en": point.get("name_en"),
                "kind": point.get("kind"),
                "is_destination": point.get("is_destination", False),
                "latitude_requested": point["latitude"],
                "longitude_requested": point["longitude"],
                "elevation_requested_m": point.get("elevation_m"),
                "coordinate_confidence": point.get("coordinate_confidence"),
                "verification_status": point.get("verification_status"),
                "retrieved_at_utc": utc_now(),
                "returned_location": {
                    "latitude": record.get("latitude"),
                    "longitude": record.get("longitude"),
                    "elevation": record.get("elevation"),
                    "generationtime_ms": record.get("generationtime_ms"),
                    "model": record.get("model"),
                    "model_version": record.get("model_version"),
                    "model_run": record.get("model_run"),
                },
                "forecast": record,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "project": "هواچ",
        "run_id": run_id,
        "retrieved_at_utc": utc_now(),
        "run_started_at_utc": started_at_utc,
        "catalog": {
            "path": str(config.catalog_path.resolve()),
            "sha256": catalog_sha256,
            "schema_version": catalog.get("schema_version"),
            "active_points": len(active_points),
            "skipped_points": skipped_points,
        },
        "request": {
            "endpoint": API_URL,
            "model_requested": config.model,
            "model_versions_returned": sorted(model_versions),
            "cell_selection": config.cell_selection,
            "timezone": config.timezone,
            "forecast_hours": config.forecast_hours,
            "hourly_variables": list(config.hourly_variables),
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "note": "Open-Meteo model output; not a local station observation.",
        },
        "points": point_payloads,
    }


def summarize_run(
    config: Config,
    checkpoint: dict[str, Any],
    finished_at_utc: str | None = None,
) -> dict[str, Any]:
    run_id = str(checkpoint["run_id"])
    batch_dir = config.batches_dir / run_id
    batch_files = sorted(batch_dir.glob("batch-*.json")) if batch_dir.exists() else []
    attempts: list[dict[str, Any]] = []
    successful_batches = 0
    failed_batches = 0
    returned_points = 0
    empty_point_ids: list[str] = []
    invalid_point_ids: list[str] = []
    batch_elapsed: list[float] = []
    model_versions: set[str] = set()
    for path in batch_files:
        try:
            batch = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(batch, dict):
            continue
        if batch.get("status") == "success":
            successful_batches += 1
        else:
            failed_batches += 1
        returned_points += int(batch.get("returned_points") or 0)
        validation = batch.get("validation") or {}
        empty_point_ids.extend(validation.get("empty_point_ids") or [])
        invalid_point_ids.extend(validation.get("invalid_point_ids") or [])
        batch_elapsed.append(float(batch.get("elapsed_seconds") or 0.0))
        for attempt in batch.get("attempts") or []:
            if isinstance(attempt, dict):
                attempts.append(attempt)
        data = batch.get("data") or []
        for record in data:
            if isinstance(record, dict):
                for field in ("model", "model_version", "model_run"):
                    if record.get(field) is not None:
                        model_versions.add(str(record[field]))
    status_counts: dict[str, int] = {}
    for attempt in attempts:
        status = str(attempt.get("http_status"))
        status_counts[status] = status_counts.get(status, 0) + 1
    http_200 = sum(1 for item in attempts if item.get("http_status") == 200)
    http_429 = sum(1 for item in attempts if item.get("http_status") == 429)
    http_5xx = sum(
        1
        for item in attempts
        if isinstance(item.get("http_status"), int) and 500 <= item["http_status"] <= 599
    )
    network_errors = sum(
        1
        for item in attempts
        if item.get("error_kind") in {"network_error", "timeout"}
    )
    retries = max(0, len(attempts) - len(batch_files))
    started = checkpoint.get("started_at_utc")
    finished_at_utc = finished_at_utc or utc_now()
    duration_seconds: float | None = None
    if started:
        try:
            duration_seconds = max(
                0.0,
                (dt.datetime.fromisoformat(finished_at_utc) - dt.datetime.fromisoformat(started)).total_seconds(),
            )
        except ValueError:
            duration_seconds = None
    completed_numbers = sorted(int(x) for x in checkpoint.get("completed_batch_numbers", []))
    total_batches = int(checkpoint.get("total_batches", 0))
    return {
        "successful_batches": successful_batches,
        "failed_batches": failed_batches,
        "unprocessed_batches": max(0, total_batches - successful_batches - failed_batches),
        "completed_batch_numbers": completed_numbers,
        "total_batches": total_batches,
        "total_points": int(checkpoint.get("total_points", 0)),
        "returned_points": returned_points,
        "http_200_responses": http_200,
        "http_429_responses": http_429,
        "http_5xx_responses": http_5xx,
        "network_errors": network_errors,
        "retry_count": retries,
        "empty_data_points": len(set(empty_point_ids)),
        "empty_data_point_ids": sorted(set(empty_point_ids)),
        "invalid_data_point_ids": sorted(set(invalid_point_ids)),
        "attempt_status_counts": status_counts,
        "model_versions_observed": sorted(model_versions),
        "average_batch_elapsed_seconds": round(sum(batch_elapsed) / len(batch_elapsed), 3) if batch_elapsed else None,
        "finished_at_utc": finished_at_utc,
        "duration_seconds": round(duration_seconds, 3) if duration_seconds is not None else None,
    }


def write_partial_manifest(config: Config, checkpoint: dict[str, Any], status: str) -> dict[str, Any]:
    updated_at_utc = utc_now()
    summary = summarize_run(config, checkpoint, updated_at_utc)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "project": "هواچ",
        "run_id": checkpoint["run_id"],
        "status": status,
        "started_at_utc": checkpoint.get("started_at_utc"),
        "updated_at_utc": updated_at_utc,
        "catalog_path": checkpoint.get("catalog_path"),
        "catalog_sha256": checkpoint.get("catalog_sha256"),
        "config": checkpoint.get("config"),
        "summary": summary,
        "batch_directory": str((config.batches_dir / checkpoint["run_id"]).resolve()),
        "latest_updated": False,
    }
    json_dump_atomic(config.runs_dir / f"{checkpoint['run_id']}.partial.json", manifest)
    return manifest


def finalize_run(
    config: Config,
    checkpoint: dict[str, Any],
    catalog: dict[str, Any],
    active_points: Sequence[dict[str, Any]],
    skipped_points: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    run_id = checkpoint["run_id"]
    latest = build_latest(
        config,
        run_id,
        catalog,
        active_points,
        skipped_points,
        checkpoint["catalog_sha256"],
        checkpoint["started_at_utc"],
    )
    # This is deliberately the first point at which latest.json is touched.
    json_dump_atomic(config.latest_path, latest)
    finished_at_utc = utc_now()
    summary = summarize_run(config, checkpoint, finished_at_utc)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "project": "هواچ",
        "run_id": run_id,
        "status": "complete",
        "started_at_utc": checkpoint["started_at_utc"],
        "finished_at_utc": finished_at_utc,
        "catalog_path": checkpoint["catalog_path"],
        "catalog_sha256": checkpoint["catalog_sha256"],
        "config": checkpoint["config"],
        "summary": summary,
        "batch_directory": str((config.batches_dir / run_id).resolve()),
        "latest_path": str(config.latest_path.resolve()),
        "latest_updated": True,
    }
    json_dump_atomic(config.runs_dir / f"{run_id}.json", manifest)
    checkpoint["status"] = "complete"
    checkpoint["finished_at_utc"] = manifest["finished_at_utc"]
    update_checkpoint(config, checkpoint)
    partial_path = config.runs_dir / f"{run_id}.partial.json"
    with contextlib.suppress(FileNotFoundError):
        partial_path.unlink()
    return manifest


def run_cycle(config: Config, logger: JsonlLogger) -> tuple[bool, dict[str, Any]]:
    catalog, active_points, skipped_points, catalog_sha256 = load_catalog(config.catalog_path)
    batches = planned_batches(active_points, config.batch_size)
    total_batches = len(batches)
    checkpoint = load_checkpoint(config)
    resumed = checkpoint is not None
    if checkpoint is None:
        checkpoint = new_checkpoint(
            config,
            run_id_now(),
            catalog,
            active_points,
            skipped_points,
            catalog_sha256,
            total_batches,
        )
        update_checkpoint(config, checkpoint)
        (config.batches_dir / checkpoint["run_id"]).mkdir(parents=True, exist_ok=True)
    else:
        # A successful batch file is the source of truth if a process died
        # after writing the file but before updating the checkpoint.
        existing_successes: list[int] = []
        for batch_number in range(1, total_batches + 1):
            path = batch_path(config, checkpoint["run_id"], batch_number)
            try:
                if read_json(path).get("status") == "success":
                    existing_successes.append(batch_number)
            except (OSError, json.JSONDecodeError, AttributeError):
                pass
        checkpoint["completed_batch_numbers"] = sorted(set(existing_successes))
        checkpoint["status"] = "running"
        update_checkpoint(config, checkpoint)
    run_id = str(checkpoint["run_id"])
    completed = set(int(x) for x in checkpoint.get("completed_batch_numbers", []))
    logger.event(
        "run_started" if not resumed else "run_resumed",
        run_id=run_id,
        total_points=len(active_points),
        total_batches=total_batches,
        completed_batches=sorted(completed),
        skipped_points=len(skipped_points),
        catalog_sha256=catalog_sha256,
        config=config.public_dict(),
    )

    rate_limit_abort = False
    for batch_number, batch in enumerate(batches, start=1):
        if batch_number in completed:
            continue
        if STOP_REQUESTED.is_set():
            break
        logger.event(
            "batch_started",
            run_id=run_id,
            batch_number=batch_number,
            total_batches=total_batches,
            point_count=len(batch),
        )
        result = process_batch(batch, batch_number, config, logger, run_id)
        json_dump_atomic(batch_path(config, run_id, batch_number), result)
        if result["status"] == "success":
            completed.add(batch_number)
            checkpoint["completed_batch_numbers"] = sorted(completed)
            checkpoint["last_successful_batch"] = batch_number
            update_checkpoint(config, checkpoint)
            logger.event(
                "batch_succeeded",
                run_id=run_id,
                batch_number=batch_number,
                returned_points=result["returned_points"],
                elapsed_seconds=result["elapsed_seconds"],
            )
        else:
            scope = None
            for attempt in reversed(result.get("attempts", [])):
                if attempt.get("rate_limit_scope"):
                    scope = attempt["rate_limit_scope"]
                    break
            logger.event(
                "batch_failed",
                level="ERROR",
                error=True,
                run_id=run_id,
                batch_number=batch_number,
                rate_limit_scope=scope,
                validation=result.get("validation", {}).get("message"),
            )
            if scope in {"hourly", "daily", "monthly"}:
                # Continuing to issue known-over-limit requests would create a
                # retry storm.  The checkpoint keeps all successful batches;
                # the next scheduled cycle resumes this run.
                rate_limit_abort = True
                break
        if batch_number < total_batches and not STOP_REQUESTED.is_set():
            if not interruptible_sleep(config.pause_seconds):
                break

    checkpoint["completed_batch_numbers"] = sorted(completed)
    complete = len(completed) == total_batches and not STOP_REQUESTED.is_set()
    if complete:
        manifest = finalize_run(config, checkpoint, catalog, active_points, skipped_points)
        logger.event(
            "run_completed",
            run_id=run_id,
            summary=manifest["summary"],
            latest_path=str(config.latest_path),
        )
        return True, manifest

    status = "shutdown" if STOP_REQUESTED.is_set() else "paused" if rate_limit_abort else "partial"
    checkpoint["status"] = status
    checkpoint["updated_at_utc"] = utc_now()
    update_checkpoint(config, checkpoint)
    manifest = write_partial_manifest(config, checkpoint, status)
    logger.event(
        "run_incomplete",
        level="WARNING",
        run_id=run_id,
        status=status,
        summary=manifest["summary"],
        latest_unchanged=True,
    )
    return False, manifest


def dry_run(config: Config) -> int:
    catalog, active_points, skipped_points, catalog_sha256 = load_catalog(config.catalog_path)
    batches = planned_batches(active_points, config.batch_size)
    report = {
        "mode": "dry_run",
        "script_version": SCRIPT_VERSION,
        "project": "هواچ",
        "catalog": {
            "path": str(config.catalog_path.resolve()),
            "sha256": catalog_sha256,
            "schema_version": catalog.get("schema_version"),
            "catalog_points": len(catalog["points"]),
            "eligible_points": len(active_points),
            "skipped_points": skipped_points,
        },
        "plan": {
            "batch_size": config.batch_size,
            "total_batches": len(batches),
            "point_readings_per_cycle": len(active_points),
            "estimated_http_requests_per_cycle": len(batches),
            "estimated_point_readings_per_day": len(active_points) * 6,
            "estimated_http_requests_per_day": len(batches) * 6,
            "pause_seconds": config.pause_seconds,
            "forecast_hours": config.forecast_hours,
            "model": config.model,
            "cell_selection": config.cell_selection,
            "hourly_variables": list(config.hourly_variables),
        },
        "batches": [
            {
                "batch_number": index,
                "point_count": len(batch),
                "first_point_id": batch[0]["id"],
                "last_point_id": batch[-1]["id"],
                "elevation_mode": "catalog" if all(point.get("elevation_m") is not None for point in batch) else "open_meteo_default_dem",
            }
            for index, batch in enumerate(batches, start=1)
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def install_signal_handlers(logger: JsonlLogger) -> None:
    def request_shutdown(signum: int, _frame: Any) -> None:
        STOP_REQUESTED.set()
        logger.event("shutdown_requested", level="WARNING", signal=signum)

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="هواچ Open-Meteo production-like collector")
    parser.add_argument("--catalog", type=Path, default=Path("hawatch_route_points_catalog.json"))
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--state-dir", type=Path, default=Path("state"))
    parser.add_argument("--logs-dir", type=Path, default=Path("logs"))
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--pause-seconds", type=float, default=10.0)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--backoff-base-seconds", type=float, default=2.0)
    parser.add_argument("--max-backoff-seconds", type=float, default=120.0)
    parser.add_argument("--minutely-wait-seconds", type=float, default=65.0)
    parser.add_argument("--forecast-hours", type=int, default=72)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--cell-selection", default=DEFAULT_CELL_SELECTION, choices=["land", "nearest", "sea"])
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument("--interval-seconds", type=float, default=4 * 60 * 60)
    parser.add_argument("--dry-run", action="store_true", help="plan and validate without calling the API")
    parser.add_argument("--daemon", action="store_true", help="run a cycle, wait, and repeat")
    parser.add_argument("--once", action="store_true", help="run one cycle; this is the default")
    return parser


def config_from_args(args: argparse.Namespace) -> Config:
    numeric_positive = {
        "batch_size": args.batch_size,
        "timeout_seconds": args.timeout_seconds,
        "max_retries": args.max_retries,
        "backoff_base_seconds": args.backoff_base_seconds,
        "max_backoff_seconds": args.max_backoff_seconds,
        "minutely_wait_seconds": args.minutely_wait_seconds,
        "forecast_hours": args.forecast_hours,
        "interval_seconds": args.interval_seconds,
    }
    for name, value in numeric_positive.items():
        if value <= 0:
            raise ValueError(f"--{name.replace('_', '-')} must be greater than zero")
    if args.pause_seconds < 0:
        raise ValueError("--pause-seconds must be zero or greater")
    return Config(
        catalog_path=args.catalog,
        data_dir=args.data_dir,
        state_dir=args.state_dir,
        logs_dir=args.logs_dir,
        batch_size=args.batch_size,
        pause_seconds=args.pause_seconds,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        backoff_base_seconds=args.backoff_base_seconds,
        max_backoff_seconds=args.max_backoff_seconds,
        minutely_wait_seconds=args.minutely_wait_seconds,
        forecast_hours=args.forecast_hours,
        model=args.model,
        cell_selection=args.cell_selection,
        timezone=args.timezone,
        interval_seconds=args.interval_seconds,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        config = config_from_args(args)
        if args.dry_run:
            return dry_run(config)
        for directory in (config.data_dir, config.runs_dir, config.batches_dir, config.state_dir, config.logs_dir):
            directory.mkdir(parents=True, exist_ok=True)
        logger = JsonlLogger(
            config.logs_dir / "hawatch-weather.jsonl",
            config.logs_dir / "hawatch-weather-error.jsonl",
        )
        install_signal_handlers(logger)
        lock = ProcessLock(config.lock_path)
        try:
            lock.__enter__()
        except RuntimeError as exc:
            logger.event("cycle_skipped_lock_held", level="WARNING", error=True, message=str(exc))
            return 2
        try:
            while not STOP_REQUESTED.is_set():
                try:
                    completed, _manifest = run_cycle(config, logger)
                except Exception as exc:  # keep daemon alive for unexpected transient failures
                    logger.event(
                        "runner_exception",
                        level="CRITICAL",
                        error=True,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                    if not args.daemon:
                        return 1
                    completed = False
                if not args.daemon or STOP_REQUESTED.is_set():
                    return 0 if completed else (130 if STOP_REQUESTED.is_set() else 1)
                logger.event(
                    "waiting_for_next_cycle",
                    interval_seconds=config.interval_seconds,
                    last_cycle_complete=completed,
                )
                if not interruptible_sleep(config.interval_seconds):
                    break
            return 130
        finally:
            lock.release()
    except (FileNotFoundError, ValueError) as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

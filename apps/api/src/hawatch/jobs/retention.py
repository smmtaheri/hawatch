"""Retention services for forecast data, Hawatch log files and OpenSearch."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import ssl
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.utils import timezone as dj_timezone

from hawatch.modules.forecasts.models import ForecastRecord


logger = logging.getLogger("hawatch.retention")
INDEX_NAME = re.compile(r"^hawatch-logs-\d{4}\.\d{2}\.\d{2}$")


def retention_days(requested: int | None = None) -> int:
    days = int(requested if requested is not None else getattr(settings, "HAWATCH_RETENTION_DAYS", 7))
    if days < 1 or days > 7:
        raise ValueError("HAWATCH_RETENTION_DAYS must be between 1 and 7")
    return days


def cleanup_forecast_data(*, days: int = 7, dry_run: bool = False) -> dict[str, int | str]:
    """Delete records whose generation time is outside the retention window.

    The current schema has hourly ``ForecastRecord`` rows only.  The optional
    model names cover the planned snapshot/assessment tables without creating
    schema changes in this observability milestone.
    """

    days = retention_days(days)
    cutoff = dj_timezone.now() - timedelta(days=days)
    result: dict[str, int | str] = {"cutoff": cutoff.isoformat(), "hourly": 0}

    hourly = ForecastRecord.objects.filter(generated_at__lt=cutoff)
    if dry_run:
        result["hourly"] = hourly.count()
    else:
        result["hourly"] = hourly.delete()[0]

    optional_specs = {
        "ForecastSnapshot": "snapshot",
        "ForecastAssessment": "assessment",
    }
    for model_name, result_key in optional_specs.items():
        try:
            model = apps.get_model("forecasts", model_name)
        except LookupError:
            result[f"{result_key}_status"] = "not_installed"
            continue
        fields = {field.name for field in model._meta.get_fields()}
        timestamp_field = next(
            (candidate for candidate in ("generated_at", "created_at", "captured_at", "forecast_at", "valid_to") if candidate in fields),
            None,
        )
        if timestamp_field is None:
            result[f"{result_key}_status"] = "no_timestamp_field"
            continue
        queryset = model.objects.filter(**{f"{timestamp_field}__lt": cutoff})
        result[result_key] = queryset.count() if dry_run else queryset.delete()[0]
        result[f"{result_key}_field"] = timestamp_field
    return result


def cleanup_log_files(*, log_dir: str | Path, days: int = 7, dry_run: bool = False) -> dict[str, int]:
    """Remove only rotated Hawatch JSONL files older than the retention window."""

    days = retention_days(days)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    directory = Path(log_dir)
    candidates = [path for path in directory.glob("*.jsonl.*") if path.is_file()]
    old = [path for path in candidates if path.stat().st_mtime < cutoff]
    if not dry_run:
        for path in old:
            path.unlink()
    return {"scanned": len(candidates), "deleted": len(old)}


def _opensearch_request(url: str, username: str, password: str, *, method: str = "GET"):
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    request = urllib.request.Request(
        url,
        method=method,
        headers={"Authorization": f"Basic {credentials}", "Accept": "application/json"},
    )
    context = ssl._create_unverified_context() if os.environ.get("OPENSEARCH_VERIFY_SSL", "false").lower() != "true" else None
    with urllib.request.urlopen(request, timeout=15, context=context) as response:
        body = response.read()
        return response.status, json.loads(body) if body else {}


def cleanup_opensearch_indices(*, url: str, username: str, password: str, days: int = 7, dry_run: bool = False) -> dict[str, int | str]:
    """Delete only date-suffixed ``hawatch-logs-*`` indices older than 7 days."""

    days = retention_days(days)
    if not url or not username or not password:
        return {"status": "not_configured", "scanned": 0, "deleted": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    endpoint = url.rstrip("/") + "/_cat/indices/hawatch-logs-*?format=json&h=index,creation.date"
    status, rows = _opensearch_request(endpoint, username, password)
    if status != 200:
        raise RuntimeError(f"OpenSearch index listing returned HTTP {status}")

    deleted = 0
    scanned = 0
    for row in rows:
        index = str(row.get("index", ""))
        if not INDEX_NAME.fullmatch(index):
            continue
        scanned += 1
        created_at = None
        raw_creation = row.get("creation.date")
        if raw_creation:
            try:
                created_at = datetime.fromtimestamp(int(raw_creation) / 1000, tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                created_at = None
        if created_at is None:
            try:
                created_at = datetime.strptime(index.rsplit("-", 1)[-1], "%Y.%m.%d").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        if created_at >= cutoff:
            continue
        if not dry_run:
            delete_status, _ = _opensearch_request(f"{url.rstrip('/')}/{index}", username, password, method="DELETE")
            if delete_status not in {200, 404}:
                raise RuntimeError(f"OpenSearch index deletion returned HTTP {delete_status} for {index}")
        deleted += 1
    return {"status": "ok", "scanned": scanned, "deleted": deleted}


def run_retention(*, days: int = 7, dry_run: bool = False, skip_opensearch: bool = False) -> dict[str, object]:
    days = retention_days(days)
    result: dict[str, object] = {
        "retention_days": days,
        "forecast": cleanup_forecast_data(days=days, dry_run=dry_run),
        "logs": cleanup_log_files(log_dir=getattr(settings, "HAWATCH_LOG_DIR", "/var/log/hawatch"), days=days, dry_run=dry_run),
    }
    if skip_opensearch:
        result["opensearch"] = {"status": "skipped", "scanned": 0, "deleted": 0}
    else:
        result["opensearch"] = cleanup_opensearch_indices(
            url=os.environ.get("OPENSEARCH_URL", ""),
            username=os.environ.get("OPENSEARCH_USERNAME", ""),
            password=os.environ.get("OPENSEARCH_PASSWORD", ""),
            days=days,
            dry_run=dry_run,
        )
    logger.info("Retention completed", extra={"event": "retention.completed", "result": result})
    return result

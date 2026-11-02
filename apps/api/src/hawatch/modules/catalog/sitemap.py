"""Build bounded sitemap snapshots; HTTP readers never generate them."""

from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Max
from django.utils.html import escape

from hawatch.modules.catalog.runtime import destination_catalog_timestamp_points, publicly_visible_weather_points
from hawatch.modules.forecasts.models import ForecastRecord
from hawatch.modules.routes.models import Route, RoutePoint

log = logging.getLogger("hawatch.sitemap")
NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
CACHE_CONTROL = "public, max-age=60, s-maxage=300"
MAX_BYTES = 50 * 1024 * 1024


def sitemap_root() -> Path:
    return Path(settings.SITEMAP_ROOT)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _latest(*timestamps):
    return max((value for value in timestamps if value is not None), default=None)


@contextmanager
def _read_snapshot():
    # Production commands own the transaction. Tests/callers may already have
    # an outer transaction; do not change its isolation or timeout settings.
    nested = connection.in_atomic_block
    with transaction.atomic():
        if not nested and connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                cursor.execute("SELECT set_config('statement_timeout', %s, true)", [str(settings.SITEMAP_QUERY_TIMEOUT_MS)])
        yield


def build_sitemap() -> tuple[bytes, dict]:
    """Keep membership/lastmod policy unchanged with one forecast aggregation."""
    with _read_snapshot():
        # Include supporting/noindex/inactive linked points too: their weather
        # can update a public route even when their own URL is not indexable.
        forecast_times = dict(
            ForecastRecord.objects.filter(
                data_mode="live", provider="open-meteo", snapshot__status__in=("success", "partial")
            ).order_by().values("weather_point_id").annotate(lastmod=Max("generated_at"))
            .values_list("weather_point_id", "lastmod")
        )
        points = list(publicly_visible_weather_points().filter(seo_indexable=True).order_by("slug")
                      .values("id", "slug", "updated_at"))
        routes = list(Route.objects.filter(is_active=True).annotate(points_updated_at=Max("points__weather_point__updated_at"))
                      .order_by("slug").values("id", "slug", "updated_at", "points_updated_at"))
        route_times = {}
        for route_id, point_id in RoutePoint.objects.filter(route__is_active=True).values_list("route_id", "weather_point_id"):
            route_times[route_id] = _latest(route_times.get(route_id), forecast_times.get(point_id))
        destination_time = destination_catalog_timestamp_points().aggregate(lastmod=Max("updated_at"))["lastmod"]

    origin = settings.PUBLIC_SITE_ORIGIN.rstrip("/")

    def entry(path, timestamp=None):
        lastmod = ""
        if timestamp is not None:
            value = timestamp.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            lastmod = f"<lastmod>{value}</lastmod>"
        return f"<url><loc>{escape(origin + path)}</loc>{lastmod}</url>"

    entries = [entry("/"), entry("/destinations", destination_time), entry("/routes")]
    entries += [entry(f"/points/{row['slug']}", _latest(row["updated_at"], forecast_times.get(row["id"]))) for row in points]
    entries += [entry(f"/routes/{row['slug']}", _latest(row["updated_at"], row["points_updated_at"], route_times.get(row["id"]))) for row in routes]
    content = (f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="{NAMESPACE}">'
               + "".join(entries) + "</urlset>").encode("utf-8")
    counts = {"points": len(points), "routes": len(routes), "urls": len(entries)}
    validate_sitemap(content, expected_count=counts["urls"])
    return content, counts


def validate_sitemap(content: bytes, *, expected_count: int | None = None):
    if not content or len(content) > MAX_BYTES or b"<!DOCTYPE" in content:
        raise ValueError("Invalid sitemap document size or declaration")
    root = ElementTree.fromstring(content)
    locations = [node.text for node in root.findall(f"{{{NAMESPACE}}}url/{{{NAMESPACE}}}loc")]
    origin = settings.PUBLIC_SITE_ORIGIN.rstrip("/")
    if root.tag != f"{{{NAMESPACE}}}urlset" or not locations or len(locations) > 50000:
        raise ValueError("Invalid sitemap namespace or URL count")
    if expected_count is not None and len(locations) != expected_count:
        raise ValueError("Sitemap membership count mismatch")
    if len(set(locations)) != len(locations):
        raise ValueError("Duplicate sitemap URL")
    for url in locations:
        if not url or not url.startswith(origin + "/") or urlsplit(url).query or urlsplit(url).fragment:
            raise ValueError("Non-canonical sitemap URL")


def _atomic_write(path: Path, content: bytes):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".sitemap-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fchmod(handle.fileno(), 0o644)
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_sitemap_status() -> dict:
    try:
        status = json.loads((sitemap_root() / "status.json").read_text(encoding="utf-8"))
        if not isinstance(status, dict):
            raise ValueError("Invalid sitemap status")
    except (OSError, ValueError):
        return {"status": "missing", "last_successful_check_at": None, "check_stale": True}
    age = None
    try:
        checked = datetime.fromisoformat(status.get("last_successful_check_at"))
        age = max(0, int((datetime.now(timezone.utc) - checked).total_seconds()))
    except (ValueError, TypeError):
        pass
    return {**status, "check_age_seconds": age,
            "check_stale": age is None or age > 3 * settings.SITEMAP_REFRESH_SECONDS}


def publish_sitemap() -> dict:
    """Serialize builders and keep the last complete file on any build error."""
    directory = sitemap_root()
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".build.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "busy"}
        previous = read_sitemap_status()
        started = time.monotonic()
        attempt = _now()
        try:
            content, counts = build_sitemap()
            validate_sitemap(content, expected_count=counts["urls"])
            target = directory / "sitemap.xml"
            old = target.read_bytes() if target.exists() else None
            changed = old != content
            if changed:
                if old:
                    try:
                        validate_sitemap(old)
                    except (ValueError, ElementTree.ParseError):
                        log.warning("Replacing an invalid existing sitemap artifact")
                    else:
                        _atomic_write(directory / "sitemap.previous.xml", old)
                _atomic_write(target, content)
            status = {
                "status": "ok", "last_attempt_at": attempt, "last_successful_check_at": _now(),
                "last_content_change_at": _now() if changed else previous.get("last_content_change_at"),
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
                "counts": counts, "sha256": hashlib.sha256(content).hexdigest(), "changed": changed,
            }
            _atomic_write(directory / "status.json", json.dumps(status).encode())
            log.info("Sitemap publication checked", extra={"event": "sitemap.published", **status})
            return status
        except Exception as exc:
            status = {**previous, "status": "failed", "last_attempt_at": attempt,
                      "error_type": type(exc).__name__, "duration_ms": round((time.monotonic() - started) * 1000, 2)}
            try:
                _atomic_write(directory / "status.json", json.dumps(status).encode())
            except OSError:
                log.exception("Cannot write sitemap status")
            raise

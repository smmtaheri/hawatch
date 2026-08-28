"""Small, dependency-free observability primitives for Hawatch.

The API deliberately exposes Prometheus' text format without adding a runtime
dependency. Database-derived gauges are scrape-accurate; request and provider
hook counters are process-local and should be replaced with a shared or
multiprocess registry when live ingestion is introduced.
"""

from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
import os
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse


_context: contextvars.ContextVar[dict[str, str]] = contextvars.ContextVar(
    "hawatch_observability_context", default={}
)
logger = logging.getLogger("hawatch.observability")


def _escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _labels(labels: dict[str, object]) -> str:
    if not labels:
        return ""
    values = ",".join(f'{key}="{_escape(labels[key])}"' for key in sorted(labels))
    return "{" + values + "}"


class JsonFormatter(logging.Formatter):
    """Emit one searchable JSON object per line, never a debug record."""

    _standard = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
        "message",
        "asctime",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "@timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": getattr(settings, "OBSERVABILITY_SERVICE_NAME", "hawatch-api"),
            "environment": getattr(settings, "OBSERVABILITY_ENVIRONMENT", "local"),
            "message": record.getMessage(),
        }
        payload.update({key: value for key, value in _context.get().items() if value})

        for key, value in record.__dict__.items():
            if key not in self._standard and not key.startswith("_"):
                try:
                    json.dumps(value)
                except (TypeError, ValueError):
                    value = str(value)
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


class SafeTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """Create the log directory before the stdlib handler opens the file."""

    def __init__(self, filename, *args, **kwargs):
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename, *args, **kwargs)


class _Metric:
    def __init__(self, name: str, kind: str, help_text: str, buckets: tuple[float, ...] = ()):
        self.name = name
        self.kind = kind
        self.help_text = help_text
        self.buckets = buckets
        self.values: OrderedDict[tuple[tuple[str, str], ...], float] = OrderedDict()
        self.histograms: OrderedDict[tuple[tuple[str, str], ...], tuple[list[float], float, float]] = OrderedDict()


class MetricsRegistry:
    def __init__(self) -> None:
        self._metrics: OrderedDict[str, _Metric] = OrderedDict()

    def counter(self, name: str, help_text: str) -> None:
        self._metrics[name] = _Metric(name, "counter", help_text)

    def gauge(self, name: str, help_text: str) -> None:
        self._metrics[name] = _Metric(name, "gauge", help_text)

    def histogram(self, name: str, help_text: str, buckets: Iterable[float]) -> None:
        self._metrics[name] = _Metric(name, "histogram", help_text, tuple(buckets))

    @staticmethod
    def _key(labels: dict[str, object] | None) -> tuple[tuple[str, str], ...]:
        return tuple(sorted((key, str(value)) for key, value in (labels or {}).items()))

    def inc(self, name: str, value: float = 1, labels: dict[str, object] | None = None) -> None:
        metric = self._metrics[name]
        key = self._key(labels)
        metric.values[key] = metric.values.get(key, 0) + value

    def set(self, name: str, value: float, labels: dict[str, object] | None = None) -> None:
        metric = self._metrics[name]
        metric.values[self._key(labels)] = value

    def observe(self, name: str, value: float, labels: dict[str, object] | None = None) -> None:
        metric = self._metrics[name]
        key = self._key(labels)
        counts, total, count = metric.histograms.setdefault(key, ([0.0] * len(metric.buckets), 0.0, 0.0))
        for index, bucket in enumerate(metric.buckets):
            if value <= bucket:
                counts[index] += 1
        metric.histograms[key] = (counts, total + value, count + 1)

    def render(self) -> str:
        lines: list[str] = []
        for metric in self._metrics.values():
            lines.append(f"# HELP {metric.name} {metric.help_text}")
            lines.append(f"# TYPE {metric.name} {metric.kind}")
            if metric.kind == "histogram":
                for key, (counts, total, count) in metric.histograms.items():
                    labels = dict(key)
                    for bucket, bucket_count in zip(metric.buckets, counts):
                        bucket_labels = {**labels, "le": str(bucket)}
                        lines.append(f"{metric.name}_bucket{_labels(bucket_labels)} {bucket_count:g}")
                    lines.append(f'{metric.name}_bucket{_labels({**labels, "le": "+Inf"})} {count:g}')
                    lines.append(f"{metric.name}_sum{_labels(labels)} {total:g}")
                    lines.append(f"{metric.name}_count{_labels(labels)} {count:g}")
            else:
                for key, value in metric.values.items():
                    lines.append(f"{metric.name}{_labels(dict(key))} {value:g}")
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()
metrics.counter("hawatch_http_requests_total", "Total HTTP requests handled by the Hawatch API.")
metrics.counter("hawatch_http_errors_total", "Total HTTP responses with a 4xx or 5xx status.")
metrics.histogram(
    "hawatch_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
metrics.gauge("hawatch_health_status", "Last observed Hawatch health status (1=healthy).")
metrics.gauge("hawatch_database_up", "Last observed database status (1=reachable).")
metrics.gauge("hawatch_catalog_destinations", "Number of active destinations in the catalog.")
metrics.gauge("hawatch_catalog_routes", "Number of active routes in the catalog.")
metrics.gauge("hawatch_catalog_weather_points", "Number of weather points in the catalog.")
metrics.gauge("hawatch_forecast_freshness_records", "Forecast records grouped by data mode and freshness.")
metrics.counter("hawatch_ingest_runs_total", "Forecast ingestion runs by provider and result.")
metrics.counter("hawatch_ingest_points_total", "Forecast points processed by provider and result.")
metrics.counter("hawatch_ingest_retries_total", "Retries made while fetching forecast data.")
metrics.gauge("hawatch_ingest_last_duration_seconds", "Duration of the latest persisted ingest run.")
metrics.gauge("hawatch_ingest_last_point_count", "Successful weather points in the latest ingest run.")
metrics.gauge("hawatch_ingest_last_requested_point_count", "Requested weather points in the latest ingest run.")
metrics.histogram(
    "hawatch_ingest_duration_seconds",
    "Forecast ingestion duration in seconds.",
    (1, 5, 15, 30, 60, 120, 300, 600),
)


def record_ingest_run(status: str, *, provider: str = "unknown", mode: str = "live") -> None:
    metrics.inc("hawatch_ingest_runs_total", labels={"mode": mode, "provider": provider, "status": status})


def record_ingest_points(count: int, status: str, *, provider: str = "unknown", mode: str = "live") -> None:
    metrics.inc(
        "hawatch_ingest_points_total",
        count,
        labels={"mode": mode, "provider": provider, "status": status},
    )


def record_ingest_retry(reason: str, *, provider: str = "unknown") -> None:
    metrics.inc("hawatch_ingest_retries_total", labels={"provider": provider, "reason": reason})


def record_ingest_duration(seconds: float, *, provider: str = "unknown") -> None:
    metrics.observe("hawatch_ingest_duration_seconds", seconds, labels={"provider": provider})


def set_health(check: str, healthy: bool) -> None:
    metrics.set("hawatch_health_status", 1 if healthy else 0, labels={"check": check})


def _set_inventory_metric(name: str, values: Iterable[tuple[dict[str, object], int]]) -> None:
    for labels, value in values:
        metrics.set(name, value, labels=labels)


def collect_database_metrics() -> None:
    """Refresh low-cardinality catalog/forecast gauges at scrape time."""

    try:
        from django.db import connection
        from django.db.models import Count

        from hawatch.modules.destinations.models import Destination
        from hawatch.modules.forecasts.models import ForecastRecord, ForecastSnapshot, WeatherPoint
        from hawatch.modules.routes.models import Route

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        metrics.set("hawatch_database_up", 1)
        metrics.set("hawatch_health_status", 1, labels={"check": "ready"})
        metrics.set("hawatch_catalog_destinations", Destination.objects.filter(is_active=True).count())
        metrics.set("hawatch_catalog_routes", Route.objects.filter(destination__is_active=True).count())
        metrics.set("hawatch_catalog_weather_points", WeatherPoint.objects.filter(destination__is_active=True).count())
        grouped = ForecastRecord.objects.values("data_mode", "freshness").annotate(count=Count("id"))
        for item in grouped:
            metrics.set(
                "hawatch_forecast_freshness_records",
                item["count"],
                labels={"data_mode": item["data_mode"], "freshness": item["freshness"]},
            )
        snapshots = ForecastSnapshot.objects.filter(provider="open-meteo")
        for status in ("success", "partial", "failed"):
            metrics.set(
                "hawatch_ingest_runs_total",
                snapshots.filter(status=status).count(),
                labels={"mode": "live", "provider": "open-meteo", "status": status},
            )
        retry_total = sum(snapshot.retry_count for snapshot in snapshots.only("retry_count"))
        metrics.set("hawatch_ingest_retries_total", retry_total, labels={"provider": "open-meteo", "reason": "all"})
        latest = snapshots.order_by("-generated_at").first()
        if latest is not None:
            metrics.set("hawatch_ingest_last_point_count", latest.point_count)
            metrics.set("hawatch_ingest_last_requested_point_count", latest.requested_point_count)
            if latest.duration_seconds is not None:
                metrics.set("hawatch_ingest_last_duration_seconds", latest.duration_seconds)
    except Exception:
        metrics.set("hawatch_database_up", 0)
        metrics.set("hawatch_health_status", 0, labels={"check": "ready"})
        logger.exception("Unable to collect database metrics", extra={"event": "metrics.collect_failed"})


def _header(request, name: str) -> str | None:
    value = request.headers.get(name, "").strip()
    if not value or len(value) > 128 or any(ord(char) < 32 for char in value):
        return None
    return value


def _request_route(request) -> str:
    match = getattr(request, "resolver_match", None)
    return getattr(match, "route", None) or request.path


class RequestMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.rstrip("/") == "/api/v1/metrics":
            return self.get_response(request)

        request_id = _header(request, "X-Request-ID") or uuid.uuid4().hex
        trace_id = _header(request, "X-Trace-ID") or request_id
        token = _context.set({"request_id": request_id, "trace_id": trace_id})
        request.request_id = request_id
        request.trace_id = trace_id
        started = time.perf_counter()
        status = 500
        response = None
        try:
            response = self.get_response(request)
            status = response.status_code
            return response
        except Exception:
            logger.exception(
                "Unhandled request error",
                extra={"event": "api.request_error", "method": request.method, "path": request.path},
            )
            raise
        finally:
            duration = time.perf_counter() - started
            route = _request_route(request)
            labels = {"method": request.method, "route": route, "status": status}
            metrics.inc("hawatch_http_requests_total", labels=labels)
            metrics.observe(
                "hawatch_http_request_duration_seconds",
                duration,
                labels={"method": request.method, "route": route},
            )
            if status >= 400:
                metrics.inc("hawatch_http_errors_total", labels={"method": request.method, "route": route, "status": status})
                if response is not None:
                    logger.warning(
                        "Request returned an error status",
                        extra={"event": "api.request_error", "method": request.method, "path": request.path, "status_code": status},
                    )
            else:
                logger.info(
                    "Request completed",
                    extra={
                        "event": "api.request_completed",
                        "method": request.method,
                        "path": request.path,
                        "status_code": status,
                        "duration_ms": round(duration * 1000, 2),
                    },
                )
            if response is not None:
                response["X-Request-ID"] = request_id
                response["X-Trace-ID"] = trace_id
            _context.reset(token)


def _metrics_token() -> str:
    path = os.environ.get("HAWATCH_METRICS_TOKEN_FILE", getattr(settings, "METRICS_TOKEN_FILE", "")).strip()
    if path:
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return os.environ.get("HAWATCH_METRICS_TOKEN", "").strip()


def metrics_view(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    expected = _metrics_token()
    if getattr(settings, "METRICS_REQUIRE_AUTH", True):
        supplied = request.headers.get("Authorization", "")
        if not expected or supplied != f"Bearer {expected}":
            return JsonResponse({"detail": "Metrics authentication required."}, status=401)
    collect_database_metrics()
    return HttpResponse(metrics.render(), content_type="text/plain; version=0.0.4; charset=utf-8")

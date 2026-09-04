"""Read-only readiness checks for the live point/route graph."""

from __future__ import annotations

from collections import Counter
from typing import Any

from hawatch.integrations.weather.ingest import snapshot_freshness
from hawatch.integrations.weather.normalize import MAX_PROVIDER_RESOLUTION_DISTANCE_KM, provider_resolution_distance_km
from hawatch.modules.catalog.runtime import ingestible_weather_points
from hawatch.modules.forecasts.models import ForecastPointResolution, ForecastRecord, ForecastSnapshot, WeatherPoint
from hawatch.modules.routes.models import Route
from hawatch.modules.routes.timing import route_timing_complete


def _add(report: dict[str, Any], level: str, message: str) -> None:
    report[level].append(message)


def _coordinate_error(point: WeatherPoint) -> str | None:
    if point.location is None:
        return f"Point {point.slug}: coordinates are missing"
    if not -90 <= float(point.location.y) <= 90 or not -180 <= float(point.location.x) <= 180:
        return f"Point {point.slug}: coordinates are outside WGS84 bounds"
    return None


def _latest_resolution(point: WeatherPoint):
    return ForecastPointResolution.objects.filter(weather_point=point, snapshot__provider="open-meteo", snapshot__status__in=("success", "partial")).select_related("snapshot").order_by("-snapshot__generated_at", "-snapshot_id").first()


def _inspect_forecast(report: dict[str, Any], point: WeatherPoint, *, require_forecast: bool) -> None:
    resolution = _latest_resolution(point)
    if resolution is None:
        _add(report, "errors" if require_forecast else "warnings", f"Point {point.slug}: no successful Open-Meteo resolution yet")
        return
    distance = provider_resolution_distance_km({"latitude": resolution.resolved_latitude, "longitude": resolution.resolved_longitude}, requested_latitude=resolution.requested_latitude, requested_longitude=resolution.requested_longitude)
    if distance is None or distance > MAX_PROVIDER_RESOLUTION_DISTANCE_KM:
        _add(report, "errors", f"Point {point.slug}: provider grid distance={distance!r} km, limit={MAX_PROVIDER_RESOLUTION_DISTANCE_KM:g} km")
    if snapshot_freshness(resolution.snapshot) != ForecastSnapshot.Freshness.READY:
        _add(report, "errors" if require_forecast else "warnings", f"Point {point.slug}: provider snapshot is not fresh")
    if not ForecastRecord.objects.filter(weather_point=point, snapshot=resolution.snapshot, data_mode="live", provider="open-meteo").exists():
        _add(report, "errors" if require_forecast else "warnings", f"Point {point.slug}: no live hourly records")
    report["summary"]["provider_checked_point_count"] += 1


def run_catalog_preflight(*, point_slug: str | None = None, require_forecast: bool = False, strict: bool = False) -> dict[str, Any]:
    report = {"point_slug": point_slug, "require_forecast": require_forecast, "errors": [], "warnings": [], "summary": {"point_count": 0, "route_count": 0, "ingestible_point_count": 0, "provider_checked_point_count": 0, "timed_route_count": 0}}
    points = WeatherPoint.objects.filter(is_active=True, data_mode="live").order_by("popular_order", "slug")
    if point_slug:
        points = points.filter(slug=point_slug)
        if not points.exists():
            _add(report, "errors", f"Point {point_slug}: not found")
    points = list(points)
    report["summary"]["point_count"] = len(points)
    routes = list(
        Route.objects.filter(
            is_active=True,
            data_mode="live",
            points__weather_point__in=points,
        )
        .distinct()
        .prefetch_related("points")
        .order_by("sort_order", "slug")
    ) if points else list(Route.objects.filter(is_active=True, data_mode="live").prefetch_related("points"))
    report["summary"]["route_count"] = len(routes)
    for route in routes:
        ordered = list(route.points.order_by("sort_order"))
        if len(ordered) < 3:
            _add(report, "errors", f"Route {route.slug}: at least three ordered points are required")
        if route.target_weather_point_id != (ordered[-1].weather_point_id if ordered else None):
            _add(report, "errors", f"Route {route.slug}: target point does not match final route point")
        if route_timing_complete(timing_status=route.timing_status, one_way_minutes=route.one_way_minutes, points=ordered):
            report["summary"]["timed_route_count"] += 1
        else:
            _add(report, "warnings", f"Route {route.slug}: timing is pending or incomplete")
    ingestible = list(ingestible_weather_points().filter(slug__in=[point.slug for point in points])) if points else list(ingestible_weather_points())
    report["summary"]["ingestible_point_count"] = len(ingestible)
    for point in ingestible:
        error = _coordinate_error(point)
        if error: _add(report, "errors", error)
        _inspect_forecast(report, point, require_forecast=require_forecast)
    report["summary"]["error_count"] = len(report["errors"])
    report["summary"]["warning_count"] = len(report["warnings"])
    report["summary"]["pass"] = not report["errors"] and (not strict or not report["warnings"])
    return report

"""Read-only catalog readiness checks for database-first operations."""

from __future__ import annotations

from collections import Counter
from typing import Any

from hawatch.integrations.weather.ingest import snapshot_freshness
from hawatch.integrations.weather.normalize import (
    MAX_PROVIDER_RESOLUTION_DISTANCE_KM,
    provider_resolution_distance_km,
)
from hawatch.modules.catalog.runtime import ingestible_weather_points
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import (
    ForecastPointResolution,
    ForecastRecord,
    ForecastSnapshot,
    WeatherPoint,
)
from hawatch.modules.routes.models import Route
from hawatch.modules.routes.timing import route_timing_complete


def _add(report: dict[str, Any], level: str, message: str) -> None:
    report[level].append(message)


def _coordinate_error(point: WeatherPoint) -> str | None:
    if point.location is None:
        return f"WeatherPoint {point.slug}: coordinates are missing"
    try:
        latitude = float(point.location.y)
        longitude = float(point.location.x)
    except (TypeError, ValueError):
        return f"WeatherPoint {point.slug}: coordinates are invalid"
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return f"WeatherPoint {point.slug}: coordinates are outside WGS84 bounds"
    return None


def _inspect_destination(report: dict[str, Any], destination: Destination) -> list[Route]:
    if not destination.is_active:
        _add(report, "errors", f"Destination {destination.slug}: is_active=false")
    if destination.data_mode != "live":
        _add(report, "errors", f"Destination {destination.slug}: data_mode={destination.data_mode!r}, expected 'live'")

    profile = destination.weather_point
    if profile is None:
        _add(report, "errors", f"Destination {destination.slug}: canonical weather_point is missing")
    else:
        if profile.kind != WeatherPoint.Kind.DESTINATION:
            _add(report, "errors", f"Destination {destination.slug}: profile point {profile.slug} is not destination-kind")
        if not profile.is_active:
            _add(report, "errors", f"WeatherPoint {profile.slug}: is_active=false")
        if not profile.ingest_enabled:
            _add(report, "errors", f"WeatherPoint {profile.slug}: ingest_enabled=false")
        if profile.data_mode != "live":
            _add(report, "errors", f"WeatherPoint {profile.slug}: data_mode={profile.data_mode!r}, expected 'live'")
        coordinate_error = _coordinate_error(profile)
        if coordinate_error:
            _add(report, "errors", coordinate_error)

    routes = list(
        destination.routes.filter(is_active=True, data_mode="live")
        .prefetch_related(
            "points__weather_point",
        )
        .order_by("sort_order", "slug")
    )
    if not routes:
        _add(report, "warnings", f"Destination {destination.slug}: no active live routes")

    rank_counts = Counter(route.sort_order for route in routes)
    for route in routes:
        if route.sort_order <= 0:
            _add(report, "warnings", f"Route {route.slug}: sort_order={route.sort_order}; assign an explicit positive rank")
    for rank, count in sorted(rank_counts.items()):
        if count > 1:
            tied = ", ".join(route.slug for route in routes if route.sort_order == rank)
            _add(report, "warnings", f"Routes share sort_order={rank}: {tied}; slug is only the deterministic tie-breaker")

    for route in routes:
        points = list(route.points.all())
        if len(points) < 2:
            _add(report, "errors", f"Route {route.slug}: at least two ordered RoutePoints are required")
            continue
        missing_points = [point.slug for point in points if point.weather_point is None]
        if missing_points:
            _add(report, "errors", f"Route {route.slug}: missing WeatherPoint link for {', '.join(missing_points)}")
            continue
        first = points[0].weather_point
        last = points[-1].weather_point
        if route.origin_weather_point_id != first.id:
            _add(report, "errors", f"Route {route.slug}: origin_weather_point does not match first RoutePoint")
        if route.target_weather_point_id != last.id:
            _add(report, "errors", f"Route {route.slug}: target_weather_point does not match last RoutePoint")
        for point in {item.weather_point for item in points}:
            if not point.is_active or not point.ingest_enabled or point.data_mode != "live":
                _add(
                    report,
                    "errors",
                    f"Route {route.slug}: point {point.slug} must be active, ingest-enabled, and live",
                )
            coordinate_error = _coordinate_error(point)
            if coordinate_error:
                _add(report, "errors", coordinate_error)
        if route_timing_complete(
            timing_status=route.timing_status,
            one_way_minutes=route.one_way_minutes,
            points=points,
        ):
            report["summary"]["timed_route_count"] += 1
        else:
            _add(report, "warnings", f"Route {route.slug}: timing is pending or incomplete; arrival weather is unavailable")

    return routes


def _latest_resolution(point: WeatherPoint) -> ForecastPointResolution | None:
    return (
        ForecastPointResolution.objects.filter(
            weather_point=point,
            snapshot__provider="open-meteo",
            snapshot__status__in=(ForecastSnapshot.Status.SUCCESS, ForecastSnapshot.Status.PARTIAL),
        )
        .select_related("snapshot")
        .order_by("-snapshot__generated_at", "-snapshot_id")
        .first()
    )


def _inspect_forecast(report: dict[str, Any], point: WeatherPoint, *, require_forecast: bool) -> None:
    resolution = _latest_resolution(point)
    if resolution is None:
        level = "errors" if require_forecast else "warnings"
        _add(report, level, f"WeatherPoint {point.slug}: no successful Open-Meteo resolution yet")
        return

    raw_resolution = {
        "latitude": resolution.resolved_latitude,
        "longitude": resolution.resolved_longitude,
    }
    distance = provider_resolution_distance_km(
        raw_resolution,
        requested_latitude=resolution.requested_latitude,
        requested_longitude=resolution.requested_longitude,
    )
    if distance is None or distance > MAX_PROVIDER_RESOLUTION_DISTANCE_KM:
        _add(
            report,
            "errors",
            f"WeatherPoint {point.slug}: provider grid distance={distance!r} km, "
            f"limit={MAX_PROVIDER_RESOLUTION_DISTANCE_KM:g} km",
        )

    snapshot = resolution.snapshot
    freshness = snapshot_freshness(snapshot)
    if freshness != ForecastSnapshot.Freshness.READY:
        level = "errors" if require_forecast else "warnings"
        _add(report, level, f"WeatherPoint {point.slug}: latest provider snapshot freshness={freshness}")

    has_hourly = ForecastRecord.objects.filter(
        weather_point=point,
        snapshot=snapshot,
        data_mode="live",
        provider="open-meteo",
    ).exists()
    if not has_hourly:
        level = "errors" if require_forecast else "warnings"
        _add(report, level, f"WeatherPoint {point.slug}: latest provider resolution has no live hourly records")

    report["summary"]["provider_checked_point_count"] += 1


def run_catalog_preflight(
    *,
    destination_slug: str | None = None,
    require_forecast: bool = False,
    strict: bool = False,
) -> dict[str, Any]:
    """Return a JSON-serializable, read-only readiness report for live DB data."""
    report: dict[str, Any] = {
        "destination_slug": destination_slug,
        "require_forecast": require_forecast,
        "errors": [],
        "warnings": [],
        "summary": {
            "destination_count": 0,
            "route_count": 0,
            "ingestible_point_count": 0,
            "provider_checked_point_count": 0,
            "timed_route_count": 0,
        },
    }

    if destination_slug:
        destinations = list(Destination.objects.filter(slug=destination_slug).select_related("weather_point"))
        if not destinations:
            _add(report, "errors", f"Destination {destination_slug}: not found")
    else:
        destinations = list(
            Destination.objects.filter(is_active=True, data_mode="live")
            .select_related("weather_point")
            .order_by("popular_order", "slug")
        )
        if not destinations:
            _add(report, "errors", "No active live destinations found")

    scoped_routes: list[Route] = []
    for destination in destinations:
        report["summary"]["destination_count"] += 1
        scoped_routes.extend(_inspect_destination(report, destination))
    report["summary"]["route_count"] = len(scoped_routes)

    if destination_slug:
        from django.db.models import Q

        points = ingestible_weather_points().filter(
            Q(destination_profile__slug=destination_slug)
            | Q(route_links__route__destination__slug=destination_slug)
        ).distinct()
    else:
        points = ingestible_weather_points()

    ingestible_points = list(points)
    report["summary"]["ingestible_point_count"] = len(ingestible_points)
    for point in ingestible_points:
        _inspect_forecast(report, point, require_forecast=require_forecast)

    report["summary"]["error_count"] = len(report["errors"])
    report["summary"]["warning_count"] = len(report["warnings"])
    report["summary"]["pass"] = not report["errors"] and (not strict or not report["warnings"])
    return report

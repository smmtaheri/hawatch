"""Database-first catalog helpers: ingest selection and revision hashing."""

from __future__ import annotations

import hashlib
import json

from django.db.models import Q, QuerySet

from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route


def ingestible_weather_points(*, slugs: list[str] | None = None) -> QuerySet[WeatherPoint]:
    """Active, ingest-enabled live points exposed by an active profile or route.

    ``WeatherPoint.destination`` is legacy/organizational ownership and does NOT
    make a point ingestible by itself.
    """
    qs = (
        WeatherPoint.objects.filter(is_active=True, ingest_enabled=True, data_mode="live")
        .exclude(slug__startswith="dest:")
        .filter(
            Q(destination_profile__is_active=True)
            | Q(route_links__route__is_active=True, route_links__route__destination__is_active=True)
            | Q(origin_routes__is_active=True, origin_routes__destination__is_active=True)
            | Q(target_routes__is_active=True, target_routes__destination__is_active=True)
        )
        .distinct()
        .order_by("slug")
    )
    if slugs:
        qs = qs.filter(slug__in=slugs)
    return qs


def publicly_visible_weather_points() -> QuerySet[WeatherPoint]:
    """Active points exposed via an active Destination profile or active Route."""
    return (
        WeatherPoint.objects.filter(is_active=True)
        .exclude(slug__startswith="dest:")
        .filter(
            Q(destination_profile__is_active=True)
            | Q(route_links__route__is_active=True, route_links__route__destination__is_active=True)
        )
        .distinct()
    )


def compute_db_catalog_revision() -> str:
    """Deterministic revision hash from active live catalog rows (not a JSON filename)."""
    payload_points = []
    for point in ingestible_weather_points():
        payload_points.append(
            {
                "slug": point.slug,
                "lat": round(point.location.y, 7) if point.location else None,
                "lon": round(point.location.x, 7) if point.location else None,
                "elevation_m": point.elevation_m,
                "status": point.status,
                "ingest_enabled": point.ingest_enabled,
            }
        )
    payload_routes = []
    for route in (
        Route.objects.filter(is_active=True, data_mode="live", destination__is_active=True).order_by("slug")
    ):
        point_slugs = list(route.points.order_by("sort_order").values_list("slug", flat=True))
        payload_routes.append(
            {
                "slug": route.slug,
                "timing_status": route.timing_status,
                "one_way_minutes": route.one_way_minutes,
                "points": point_slugs,
            }
        )
    blob = json.dumps({"points": payload_points, "routes": payload_routes}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"dbrev-{digest[:16]}"


def live_catalog_is_empty() -> bool:
    return not (
        WeatherPoint.objects.filter(data_mode="live")
        .exclude(slug__startswith="dest:")
        .exists()
    )

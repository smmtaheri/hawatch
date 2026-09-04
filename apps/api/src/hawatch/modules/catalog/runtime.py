"""Database-first catalog helpers for the point/route graph."""

from __future__ import annotations

import hashlib
import json

from django.db.models import Q, QuerySet

from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route


def ingestible_weather_points(*, slugs: list[str] | None = None) -> QuerySet[WeatherPoint]:
    qs = (
        WeatherPoint.objects.filter(is_active=True, ingest_enabled=True, data_mode="live")
        .exclude(Q(slug__startswith="dest:") | Q(slug__startswith="route:"))
        .filter(Q(seo_indexable=True) | Q(route_links__route__is_active=True))
        .distinct()
        .order_by("slug")
    )
    if slugs:
        qs = qs.filter(slug__in=slugs)
    return qs


def publicly_visible_weather_points() -> QuerySet[WeatherPoint]:
    return (
        WeatherPoint.objects.filter(is_active=True)
        .exclude(Q(slug__startswith="dest:") | Q(slug__startswith="route:"))
        .filter(Q(seo_indexable=True) | Q(route_links__route__is_active=True))
        .distinct()
    )


def compute_db_catalog_revision() -> str:
    payload_points = [
        {
            "slug": point.slug,
            "lat": round(point.location.y, 7) if point.location else None,
            "lon": round(point.location.x, 7) if point.location else None,
            "elevation_m": point.elevation_m,
            "status": point.status,
            "ingest_enabled": point.ingest_enabled,
        }
        for point in ingestible_weather_points()
    ]
    payload_routes = []
    for route in Route.objects.filter(is_active=True, data_mode="live").order_by("slug"):
        payload_routes.append(
            {
                "slug": route.slug,
                "timing_status": route.timing_status,
                "one_way_minutes": route.one_way_minutes,
                "points": list(route.points.order_by("sort_order").values_list("slug", flat=True)),
            }
        )
    blob = json.dumps({"points": payload_points, "routes": payload_routes}, sort_keys=True, separators=(",", ":"))
    return f"dbrev-{hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]}"


def live_catalog_is_empty() -> bool:
    return not WeatherPoint.objects.filter(data_mode="live", is_active=True).exclude(Q(slug__startswith="dest:") | Q(slug__startswith="route:")).exists()

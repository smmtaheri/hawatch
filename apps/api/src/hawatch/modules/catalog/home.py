"""Small, cached data shared by the home page HTML and API fallback."""

from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

from hawatch.common.time import to_fa_digits
from hawatch.integrations.weather.ingest import latest_snapshot, snapshot_freshness
from hawatch.modules.analytics.models import PageViewEvent
from hawatch.modules.catalog.identity import category_key_for_point
from hawatch.modules.catalog.runtime import ordered_publicly_visible_destinations
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route


HOME_CATALOG_CACHE_KEY = "hawatch:home-catalog:v1"
HOME_CATALOG_CACHE_SECONDS = 300
HOME_POPULAR_DESTINATION_COUNT = 4


def home_catalog_data() -> dict:
    """Return home cards ranked by unique destination visitors in seven days.

    The window follows the analytics UI: today and the six preceding Tehran
    calendar dates. Ties retain the curated home order, then use the slug for
    deterministic results. Only independent, indexable destinations count;
    route pages and technical route waypoints are excluded.
    """

    try:
        cached = cache.get(HOME_CATALOG_CACHE_KEY)
    except Exception:
        cached = None
    if isinstance(cached, dict):
        return cached

    now = timezone.localtime()
    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)
    destinations = list(
        ordered_publicly_visible_destinations().values(
            "slug",
            "name",
            "page_name",
            "short_label",
            "tile_name",
            "short_category",
            "category",
            "category_key",
            "place_type",
            "region",
            "elevation_m",
            "image",
            "image_alt",
            "is_popular",
            "popular_order",
            "seo_indexable",
            "data_mode",
            "location",
        )
    )
    slugs = [point["slug"] for point in destinations]
    visits = {
        row["page_slug"]: row["unique_visitors"]
        for row in PageViewEvent.objects.filter(
            page_type=PageViewEvent.PageType.POINT,
            page_slug__in=slugs,
            occurred_at__gte=window_start,
        )
        .values("page_slug")
        .annotate(unique_visitors=Count("visitor_hash", distinct=True))
    }
    destinations.sort(
        key=lambda point: (
            -visits.get(point["slug"], 0),
            -int(point["is_popular"]),
            point["popular_order"],
            point["slug"],
        )
    )

    popular_points = []
    for point in destinations[:HOME_POPULAR_DESTINATION_COUNT]:
        elevation = point["elevation_m"]
        location = point["location"]
        name = point["page_name"] or point["name"]
        popular_points.append(
            {
                "slug": point["slug"],
                "tile_name": point["tile_name"] or point["short_label"] or point["name"],
                "name": name,
                "short_category": point["short_category"],
                "category": point["category"],
                "category_key": category_key_for_point(point["category_key"], point["place_type"]),
                "place_type": point["place_type"],
                "region": point["region"],
                "elevation_m": elevation,
                "elevation_label": f"{to_fa_digits(elevation)} متر" if elevation is not None else "ارتفاع نامشخص",
                "image": point["image"],
                "image_alt": point["image_alt"],
                "href": f"/points/{point['slug']}",
                "is_popular": point["is_popular"],
                "seo_indexable": point["seo_indexable"],
                "latitude": location.y if location else None,
                "longitude": location.x if location else None,
                "data_mode": point["data_mode"],
                "weather_point_slug": point["slug"],
            }
        )

    snapshot = latest_snapshot()
    data = {
        "popular_points": popular_points,
        "catalog_counts": {
            "points": WeatherPoint.objects.filter(is_active=True).count(),
            "routes": Route.objects.filter(is_active=True).count(),
        },
        "freshness": snapshot_freshness(snapshot),
    }
    try:
        cache.set(HOME_CATALOG_CACHE_KEY, data, timeout=HOME_CATALOG_CACHE_SECONDS)
    except Exception:
        pass
    return data

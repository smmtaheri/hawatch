"""Compact public search catalog for browser and edge caching."""

from __future__ import annotations

import hashlib
import json

from django.core.cache import cache
from django.db.models import Prefetch

from hawatch.modules.catalog.identity import category_key_for_point
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint

SEARCH_INDEX_CACHE_KEY = "catalog:search-index:v1"
SEARCH_INDEX_CACHE_SECONDS = 300


def invalidate_search_index_payload() -> None:
    cache.delete(SEARCH_INDEX_CACHE_KEY)


def _build_search_index() -> dict:
    points = []
    queryset = WeatherPoint.objects.filter(is_active=True).exclude(slug__startswith="dest:").exclude(
        slug__startswith="route:"
    ).order_by("importance", "popular_order", "page_name", "slug")
    for point in queryset.only(
        "slug", "name", "page_name", "aliases", "importance", "region", "elevation_m",
        "category_key", "place_type",
    ):
        terms = list(dict.fromkeys(
            value.strip()
            for value in [point.name, point.page_name, *(point.aliases or [])]
            if value and value.strip()
        ))
        if not terms:
            continue
        hint = " · ".join(filter(None, [
            point.region,
            f"{point.elevation_m} متر" if point.elevation_m is not None else "",
        ]))
        points.append({
            "slug": point.slug,
            "label": point.page_name or point.name,
            "terms": terms,
            "hint": hint,
            "href": f"/points/{point.slug}",
            "category_key": category_key_for_point(point.category_key, point.place_type),
            "place_type": point.place_type,
            "primary": point.importance == "primary",
        })

    route_points = RoutePoint.objects.select_related("weather_point").order_by("sort_order", "pk")
    routes = []
    for route in Route.objects.filter(is_active=True).order_by("sort_order", "slug").prefetch_related(
        Prefetch("points", queryset=route_points)
    ):
        linked_points = list(route.points.all())
        terms = list(dict.fromkeys(value.strip() for value in [
            route.title,
            route.origin,
            route.target_label,
            route.region,
            *(point.weather_point.name for point in linked_points if point.weather_point_id),
        ] if value and value.strip()))
        if not terms:
            continue
        count = len(linked_points)
        hint = f"{count} نقطه"
        if route.distance_km is not None:
            hint += f" · {route.distance_km} کیلومتر"
        routes.append({
            "slug": route.slug,
            "label": route.title,
            "terms": terms,
            "hint": hint,
            "href": f"/routes/{route.slug}",
        })

    payload = {"points": points, "routes": routes}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["revision"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    return payload


def search_index_payload() -> dict:
    payload = cache.get(SEARCH_INDEX_CACHE_KEY)
    if payload is None:
        payload = _build_search_index()
        cache.set(SEARCH_INDEX_CACHE_KEY, payload, SEARCH_INDEX_CACHE_SECONDS)
    return payload

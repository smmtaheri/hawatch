"""Static and database checks for catalog identity and route integrity."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from hawatch.modules.catalog.identity import (
    IDENTITY_IMPORTANCE,
    NAME_STATUSES,
    PLACE_TYPES,
    SLUG_RE,
    normalize_identity_text,
)


@dataclass(frozen=True)
class CatalogIssue:
    level: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper()} [{self.code}] {self.message}"


def _issue(level: str, code: str, message: str) -> CatalogIssue:
    return CatalogIssue(level, code, message)


def validate_catalog_document(data: dict[str, Any]) -> list[CatalogIssue]:
    """Validate a JSON catalog without touching Django or the database."""
    issues: list[CatalogIssue] = []
    if not isinstance(data, dict):
        return [_issue("error", "document", "catalog must be an object")]

    for key in ("catalog_version", "destination", "weather_points", "routes"):
        if key not in data:
            issues.append(_issue("error", "required", f"missing required key: {key}"))
    if issues:
        return issues

    destination = data["destination"]
    if not isinstance(destination, dict):
        return [_issue("error", "destination", "destination must be an object")]
    destination_slug = str(destination.get("slug") or "")
    if not SLUG_RE.fullmatch(destination_slug):
        issues.append(_issue("error", "destination-slug", f"invalid destination slug: {destination_slug!r}"))

    point_rows = data.get("weather_points") or {}
    if not isinstance(point_rows, dict) or not point_rows:
        issues.append(_issue("error", "points", "weather_points must be a non-empty object"))
        return issues
    shared = data.get("shared_weather_points") or []
    if not isinstance(shared, list) or len(shared) != len(set(shared)):
        issues.append(_issue("error", "shared-points", "shared_weather_points must be a unique list"))
        shared = []
    point_slugs = set(point_rows) | set(shared)
    destination_point = data.get("destination_weather_point")
    if destination_point not in point_slugs:
        issues.append(_issue("error", "destination-point", f"destination weather point is missing: {destination_point!r}"))

    page_names: dict[str, list[str]] = defaultdict(list)
    aliases: dict[str, list[str]] = defaultdict(list)
    for slug, row in point_rows.items():
        is_destination_point = slug == destination_point and isinstance(row, dict) and row.get("kind") == "destination"
        if not isinstance(slug, str) or (not SLUG_RE.fullmatch(slug) and not is_destination_point):
            issues.append(_issue("error", "point-slug", f"invalid point slug: {slug!r}; use lowercase hyphens"))
        if not isinstance(row, dict):
            issues.append(_issue("error", "point", f"point {slug!r} must be an object"))
            continue
        required = ("name", "page_name", "short_label", "place_type", "identity_summary", "importance", "name_status", "source_urls")
        for key in required:
            value = row.get(key)
            if value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, list) and not value):
                issues.append(_issue("error", "point-metadata", f"point {slug!r} is missing {key}"))
        page_name = str(row.get("page_name") or "")
        if page_name:
            page_names[normalize_identity_text(page_name)].append(slug)
        for alias in row.get("aliases") or []:
            aliases[normalize_identity_text(alias)].append(slug)
        if row.get("place_type") not in PLACE_TYPES:
            issues.append(_issue("error", "place-type", f"point {slug!r} has invalid place_type={row.get('place_type')!r}"))
        if row.get("importance") not in IDENTITY_IMPORTANCE:
            issues.append(_issue("error", "importance", f"point {slug!r} has invalid importance={row.get('importance')!r}"))
        if row.get("name_status") not in NAME_STATUSES:
            issues.append(_issue("error", "name-status", f"point {slug!r} has invalid name_status={row.get('name_status')!r}"))
        sources = row.get("source_urls")
        if sources and (not isinstance(sources, list) or not all(isinstance(url, str) and url.strip() for url in sources)):
            issues.append(_issue("error", "sources", f"point {slug!r} source_urls must contain URL strings"))
        latitude = row.get("latitude")
        longitude = row.get("longitude")
        if not isinstance(latitude, (int, float)) or not -90 <= latitude <= 90:
            issues.append(_issue("error", "coordinates", f"point {slug!r} has invalid latitude"))
        if not isinstance(longitude, (int, float)) or not -180 <= longitude <= 180:
            issues.append(_issue("error", "coordinates", f"point {slug!r} has invalid longitude"))
        elevation = row.get("elevation_m")
        if elevation is not None and (not isinstance(elevation, (int, float)) or not 0 <= elevation <= 9000):
            issues.append(_issue("error", "elevation", f"point {slug!r} has invalid elevation"))

    for normalized, slugs in page_names.items():
        if normalized and len(slugs) > 1:
            issues.append(_issue("error", "duplicate-page-name", f"page_name collision: {', '.join(slugs)}"))
    for normalized, slugs in aliases.items():
        if normalized and len(set(slugs)) > 1:
            issues.append(_issue("warning", "alias-collision", f"alias collision: {', '.join(slugs)}"))

    routes = data.get("routes")
    if not isinstance(routes, dict):
        issues.append(_issue("error", "routes", "routes must be an object; use {} for destination-only"))
        return issues
    route_orders: list[tuple[int, str]] = []
    for route_key, route in routes.items():
        if not isinstance(route, dict):
            issues.append(_issue("error", "route", f"route {route_key!r} must be an object"))
            continue
        slug = str(route.get("slug") or "")
        if not SLUG_RE.fullmatch(slug):
            issues.append(_issue("error", "route-slug", f"invalid route slug: {slug!r}"))
        points = route.get("points") or []
        if len(points) < 3:
            issues.append(_issue("error", "route-chain", f"route {slug or route_key!r} needs origin, real mid landmark and destination"))
        if len(points) != len(set(points)):
            issues.append(_issue("error", "route-duplicates", f"route {slug or route_key!r} repeats a point"))
        for point_slug in points:
            if point_slug not in point_slugs:
                issues.append(_issue("error", "route-reference", f"route {slug or route_key!r} references missing point {point_slug!r}"))
        notes = route.get("public_point_notes") or {}
        if set(notes) - set(points):
            issues.append(_issue("error", "route-notes", f"route {slug or route_key!r} notes reference points outside route"))
        route_orders.append((int(route.get("sort_order", 0)), slug or route_key))
    if len(route_orders) != len({slug for _order, slug in route_orders}):
        issues.append(_issue("error", "route-slug", "route slug is not unique"))
    if len(route_orders) != len({order for order, _slug in route_orders}):
        issues.append(_issue("error", "route-order", "route sort_order is not unique"))
    return issues


def _distance_m(first: Any, second: Any) -> float:
    lat1, lon1 = math.radians(first.location.y), math.radians(first.location.x)
    lat2, lon2 = math.radians(second.location.y), math.radians(second.location.x)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_000 * 2 * math.asin(min(1, math.sqrt(a)))


def validate_database_catalog(*, strict: bool = False) -> list[CatalogIssue]:
    """Validate the current DB after a migration/import; never mutates it."""
    from hawatch.modules.destinations.models import Destination
    from hawatch.modules.forecasts.models import WeatherPoint
    from hawatch.modules.routes.models import Route

    issues: list[CatalogIssue] = []
    points = list(WeatherPoint.objects.filter(is_active=True).select_related("destination"))
    destinations = list(Destination.objects.filter(is_active=True))
    seen_slugs: dict[str, int] = {}
    seen_names: dict[str, list[str]] = defaultdict(list)
    for point in points:
        if point.slug.startswith("dest:"):
            issues.append(_issue("error", "synthetic-point", f"synthetic point remains active: {point.slug}"))
        if not SLUG_RE.fullmatch(point.slug) and point.kind != WeatherPoint.Kind.DESTINATION:
            issues.append(_issue("error", "point-slug", f"invalid DB point slug: {point.slug}"))
        if "_" in point.slug and point.kind != WeatherPoint.Kind.DESTINATION:
            issues.append(_issue("error", "underscore-slug", f"independent point still uses underscore: {point.slug}"))
        if not point.page_name or not point.short_label or not point.place_type or not point.identity_summary or not point.source_urls:
            issues.append(_issue("error", "point-metadata", f"point metadata incomplete: {point.slug}"))
        if point.page_name:
            seen_names[normalize_identity_text(point.page_name)].append(point.slug)
        seen_slugs[point.slug] = seen_slugs.get(point.slug, 0) + 1
    for slug, count in seen_slugs.items():
        if count > 1:
            issues.append(_issue("error", "duplicate-slug", f"duplicate DB point slug: {slug}"))
    for normalized, slugs in seen_names.items():
        if normalized and len(slugs) > 1:
            issues.append(_issue("error", "duplicate-page-name", f"duplicate DB page_name: {', '.join(slugs)}"))
    for index, first in enumerate(points):
        for second in points[index + 1 :]:
            distance = _distance_m(first, second)
            if distance < 25:
                issues.append(_issue("error", "near-duplicate-point", f"points {first.slug} and {second.slug} are {distance:.1f}m apart"))
            elif distance < 100:
                issues.append(_issue("warning", "near-point", f"points {first.slug} and {second.slug} are {distance:.1f}m apart; curator review required"))
    for destination in destinations:
        if destination.weather_point_id is None:
            issues.append(_issue("error", "destination-point", f"destination has no canonical WeatherPoint: {destination.slug}"))
        elif destination.weather_point.kind != WeatherPoint.Kind.DESTINATION:
            issues.append(_issue("error", "destination-kind", f"destination point is not destination-kind: {destination.slug}"))
        for route in destination.routes.filter(is_active=True).prefetch_related("points"):
            ordered = list(route.points.order_by("sort_order"))
            if len(ordered) < 3:
                issues.append(_issue("error", "route-chain", f"route needs at least three points: {route.slug}"))
            if [item.sort_order for item in ordered] != sorted({item.sort_order for item in ordered}):
                issues.append(_issue("error", "route-order", f"route point order is invalid: {route.slug}"))
            for point in ordered:
                if point.weather_point_id is None:
                    issues.append(_issue("error", "route-reference", f"route point has no WeatherPoint: {route.slug}:{point.slug}"))
    return issues


def format_issues(issues: Iterable[CatalogIssue]) -> str:
    return "\n".join(str(issue) for issue in issues)

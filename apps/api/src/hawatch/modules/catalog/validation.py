"""Static and database validation for the point/route graph."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from hawatch.modules.catalog.identity import IDENTITY_IMPORTANCE, NAME_STATUSES, PLACE_TYPES, SLUG_RE, normalize_identity_text


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
    issues: list[CatalogIssue] = []
    if not isinstance(data, dict):
        return [_issue("error", "document", "catalog must be an object")]
    for key in ("catalog_version", "point", "weather_points", "routes"):
        if key not in data:
            issues.append(_issue("error", "required", f"missing required key: {key}"))
    if issues:
        return issues
    profile = data["point"]
    if not isinstance(profile, dict) or not SLUG_RE.fullmatch(str(profile.get("slug") or "")):
        issues.append(_issue("error", "point-profile", "point.slug must be a lowercase hyphen slug"))
    point_rows = data["weather_points"]
    if not isinstance(point_rows, dict) or not point_rows:
        return issues + [_issue("error", "points", "weather_points must be a non-empty object")]
    shared = data.get("shared_weather_points") or []
    if not isinstance(shared, list) or len(shared) != len(set(shared)):
        issues.append(_issue("error", "shared-points", "shared_weather_points must be a unique list"))
        shared = []
    point_slugs = set(point_rows) | set(shared)
    primary_slug = str(data.get("primary_point") or profile.get("slug") or "")
    if primary_slug not in point_slugs:
        issues.append(_issue("error", "primary-point", f"primary point is missing: {primary_slug!r}"))
    page_names: dict[str, list[str]] = defaultdict(list)
    aliases: dict[str, list[str]] = defaultdict(list)
    for slug, row in point_rows.items():
        if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
            issues.append(_issue("error", "point-slug", f"invalid point slug: {slug!r}"))
        if not isinstance(row, dict):
            issues.append(_issue("error", "point", f"point {slug!r} must be an object"))
            continue
        for key in ("name", "page_name", "short_label", "place_type", "identity_summary", "importance", "name_status", "source_urls"):
            if not row.get(key):
                issues.append(_issue("error", "point-metadata", f"point {slug!r} is missing {key}"))
        if row.get("place_type") not in PLACE_TYPES:
            issues.append(_issue("error", "place-type", f"point {slug!r} has invalid place_type"))
        if row.get("importance") not in IDENTITY_IMPORTANCE:
            issues.append(_issue("error", "importance", f"point {slug!r} has invalid importance"))
        if row.get("name_status") not in NAME_STATUSES:
            issues.append(_issue("error", "name-status", f"point {slug!r} has invalid name_status"))
        if not isinstance(row.get("source_urls"), list) or not all(isinstance(url, str) and url.strip() for url in row.get("source_urls", [])):
            issues.append(_issue("error", "sources", f"point {slug!r} source_urls must contain URL strings"))
        if not isinstance(row.get("latitude"), (int, float)) or not -90 <= row.get("latitude") <= 90:
            issues.append(_issue("error", "coordinates", f"point {slug!r} has invalid latitude"))
        if not isinstance(row.get("longitude"), (int, float)) or not -180 <= row.get("longitude") <= 180:
            issues.append(_issue("error", "coordinates", f"point {slug!r} has invalid longitude"))
        page_names[normalize_identity_text(row.get("page_name", ""))].append(slug)
        for alias in row.get("aliases") or []:
            aliases[normalize_identity_text(alias)].append(slug)
    for normalized, slugs in page_names.items():
        if normalized and len(slugs) > 1:
            issues.append(_issue("error", "duplicate-page-name", f"page_name collision: {', '.join(slugs)}"))
    for normalized, slugs in aliases.items():
        if normalized and len(set(slugs)) > 1:
            issues.append(_issue("warning", "alias-collision", f"alias collision: {', '.join(slugs)}"))
    route_orders: list[tuple[int, str]] = []
    for route_key, route in data["routes"].items():
        if not isinstance(route, dict):
            issues.append(_issue("error", "route", f"route {route_key!r} must be an object")); continue
        slug = str(route.get("slug") or "")
        if not SLUG_RE.fullmatch(slug):
            issues.append(_issue("error", "route-slug", f"invalid route slug: {slug!r}"))
        points = route.get("points") or []
        if len(points) < 3:
            issues.append(_issue("error", "route-chain", f"route {slug or route_key!r} needs origin, landmark and target"))
        if len(points) != len(set(points)):
            issues.append(_issue("error", "route-duplicates", f"route {slug or route_key!r} repeats a point"))
        for point_slug in points:
            if point_slug not in point_slugs:
                issues.append(_issue("error", "route-reference", f"route {slug or route_key!r} references missing point {point_slug!r}"))
        route_orders.append((int(route.get("sort_order", 0)), slug or route_key))
    if len(route_orders) != len({slug for _order, slug in route_orders}):
        issues.append(_issue("error", "route-slug", "route slug is not unique"))
    return issues


def _distance_m(first: Any, second: Any) -> float:
    lat1, lon1 = math.radians(first.location.y), math.radians(first.location.x)
    lat2, lon2 = math.radians(second.location.y), math.radians(second.location.x)
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6_371_000 * 2 * math.asin(min(1, math.sqrt(a)))


def validate_database_catalog(*, strict: bool = False) -> list[CatalogIssue]:
    from hawatch.modules.forecasts.models import WeatherPoint
    from hawatch.modules.routes.models import Route

    issues: list[CatalogIssue] = []
    points = list(WeatherPoint.objects.filter(is_active=True))
    names: dict[str, list[str]] = defaultdict(list)
    for point in points:
        if point.slug.startswith(("dest:", "route:")) or not SLUG_RE.fullmatch(point.slug) or "_" in point.slug:
            issues.append(_issue("error", "point-slug", f"invalid DB point slug: {point.slug}"))
        if not point.page_name or not point.short_label or not point.place_type or not point.identity_summary or not point.source_urls:
            issues.append(_issue("error", "point-metadata", f"point metadata incomplete: {point.slug}"))
        names[normalize_identity_text(point.page_name)].append(point.slug)
    for normalized, slugs in names.items():
        if normalized and len(slugs) > 1:
            issues.append(_issue("error", "duplicate-page-name", f"duplicate page_name: {', '.join(slugs)}"))
    for index, first in enumerate(points):
        for second in points[index + 1 :]:
            distance = _distance_m(first, second)
            if distance < 25:
                issues.append(_issue("error", "near-duplicate-point", f"points {first.slug} and {second.slug} are {distance:.1f}m apart; merge them before publish"))
            elif distance < 100:
                issues.append(_issue("warning", "near-point", f"points {first.slug} and {second.slug} are {distance:.1f}m apart; curator review required"))
    for route in Route.objects.filter(is_active=True).prefetch_related("points"):
        ordered = list(route.points.order_by("sort_order"))
        if len(ordered) < 3:
            issues.append(_issue("error", "route-chain", f"route needs at least three points: {route.slug}"))
        if [item.sort_order for item in ordered] != sorted({item.sort_order for item in ordered}):
            issues.append(_issue("error", "route-order", f"route point order is invalid: {route.slug}"))
        for item in ordered:
            if item.weather_point_id is None:
                issues.append(_issue("error", "route-reference", f"route point has no point: {route.slug}:{item.slug}"))
    return issues


def format_issues(issues: Iterable[CatalogIssue]) -> str:
    return "\n".join(str(issue) for issue in issues)

"""Explicit, database-first synchronization for the packaged catalog set."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q

from hawatch.modules.catalog.catalog import _route_distance_km, _validate_document_shape, load_catalog_file, seed_catalog
from hawatch.modules.catalog.identity import metadata_for_point
from hawatch.modules.catalog.search import rebuild_search_index
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route


@dataclass(frozen=True)
class DesiredCatalog:
    files: tuple[tuple[str, dict[str, Any]], ...]
    point_slugs: frozenset[str]
    point_versions: dict[str, str]
    point_rows: dict[str, dict[str, Any]]
    point_profiles: dict[str, dict[str, Any]]
    route_slugs: frozenset[str]
    route_versions: dict[str, str]
    route_rows: dict[str, dict[str, Any]]
    route_catalog_keys: dict[str, str]
    route_point_slugs: dict[str, frozenset[str]]


def load_packaged_catalogs() -> DesiredCatalog:
    fixtures = Path(settings.FIXTURES_DIR).resolve()
    files: list[tuple[str, dict[str, Any]]] = []
    point_slugs: set[str] = set()
    point_versions: dict[str, str] = {}
    point_rows: dict[str, dict[str, Any]] = {}
    point_profiles: dict[str, dict[str, Any]] = {}
    route_slugs: set[str] = set()
    route_versions: dict[str, str] = {}
    route_rows: dict[str, dict[str, Any]] = {}
    route_catalog_keys: dict[str, str] = {}
    route_point_slugs: dict[str, frozenset[str]] = {}
    for path in sorted((fixtures / "catalog").glob("*_v*.json")):
        relative = path.relative_to(fixtures).as_posix()
        data = load_catalog_file(relative)
        _validate_document_shape(data)
        files.append((relative, data))
        version = str(data["catalog_version"])
        local_points = set(data["weather_points"])
        for slug, row in data["weather_points"].items():
            previous = point_versions.get(slug)
            if previous:
                raise ValueError(f"Point slug {slug!r} is owned by multiple catalog versions: {previous}, {version}")
            point_versions[slug] = version
            point_rows[slug] = row
            point_profiles[slug] = data["point"]
        point_slugs.update(local_points)
        point_slugs.update(data.get("shared_weather_points") or [])
        for catalog_key, route in data["routes"].items():
            slug = str(route["slug"])
            if slug in route_slugs:
                raise ValueError(f"Route slug is duplicated across catalog files: {slug}")
            route_slugs.add(slug)
            route_versions[slug] = version
            route_rows[slug] = route
            route_catalog_keys[slug] = str(catalog_key)
            route_point_slugs[slug] = frozenset(route["points"])
    if not files:
        raise ValueError("No catalog fixtures found")
    return DesiredCatalog(
        tuple(files), frozenset(point_slugs), point_versions, point_rows, point_profiles,
        frozenset(route_slugs), route_versions, route_rows, route_catalog_keys, route_point_slugs,
    )


def _point_state(point: WeatherPoint) -> tuple[Any, ...]:
    location = point.location
    return (
        point.name,
        point.page_name,
        tuple(point.aliases or []),
        point.seo_indexable,
        point.climate,
        point.is_active,
        point.catalog_version,
        round(location.y, 7) if location else None,
        round(location.x, 7) if location else None,
        point.elevation_m,
        point.status,
    )


def _route_state(route: Route) -> tuple[Any, ...]:
    return (
        route.title,
        route.subtitle,
        route.trail_label,
        route.origin,
        route.target_label,
        route.region,
        route.distance_km,
        route.ascent_m,
        route.catalog_key,
        route.seed_version,
        route.is_active,
        tuple(route.points.order_by("sort_order", "pk").values_list("slug", flat=True)),
    )


def _linked_point_conflict(point: WeatherPoint) -> str | None:
    if point.route_links.filter(fixture_managed=False).exists():
        return "linked by operator-managed RoutePoint rows"
    if Route.objects.filter(
        Q(origin_weather_point=point) | Q(target_weather_point=point), fixture_managed=False
    ).exists():
        return "referenced by operator-managed route endpoint rows"
    return None


def _point_matches_catalog(point: WeatherPoint, slug: str, desired: DesiredCatalog) -> bool:
    row = desired.point_rows.get(slug)
    profile = desired.point_profiles.get(slug)
    if row is None or profile is None:
        # Shared points are owned by their canonical catalog and are not
        # overwritten by a catalog that merely references them.
        return True
    kind = row.get("kind") or WeatherPoint.Kind.SHARED
    identity = metadata_for_point(
        slug,
        row,
        primary_label=str(profile.get("name") or ""),
        is_primary=kind == WeatherPoint.Kind.PRIMARY,
    )
    expected = {
        "name": identity["name"],
        "page_name": identity["page_name"],
        "short_label": identity["short_label"],
        "aliases": identity["aliases"],
        "climate": row.get("climate") or profile.get("climate", "alpine"),
        "elevation_m": row.get("elevation_m"),
        "status": row.get("status") or (WeatherPoint.Status.UNRESOLVED_ELEVATION if row.get("elevation_m") is None else WeatherPoint.Status.APPROVED),
        "seo_indexable": bool(profile.get("seo_indexable", True)),
        "is_active": bool(row.get("is_active", profile.get("is_active", True))),
    }
    return all(getattr(point, field) == value for field, value in expected.items()) and point.catalog_version == desired.point_versions[slug]


def _route_matches_catalog(route: Route, slug: str, desired: DesiredCatalog) -> bool:
    row = desired.route_rows[slug]
    expected = {
        "title": row.get("title", ""),
        "subtitle": row.get("subtitle", ""),
        "trail_label": row.get("trail_label", ""),
        "origin": row.get("origin", ""),
        "target_label": row.get("target_label", ""),
        "region": row.get("region", ""),
        "distance_km": _route_distance_km(row.get("distance_km")),
        "ascent_m": row.get("ascent_m"),
        "featured": bool(row.get("featured", False)),
        "sort_order": row.get("sort_order", 0),
        "catalog_key": desired.route_catalog_keys[slug],
    }
    return (
        all(getattr(route, field) == value for field, value in expected.items())
        and tuple(route.points.order_by("sort_order", "pk").values_list("slug", flat=True)) == tuple(row.get("points", []))
        and route.seed_version == desired.route_versions[slug]
    )


def build_sync_plan(desired: DesiredCatalog) -> dict[str, Any]:
    points = {point.slug: point for point in WeatherPoint.objects.all()}
    routes = {route.slug: route for route in Route.objects.all()}
    # Only locally owned fixture rows may be created. A missing shared
    # reference is a conflict, never an implicit new point.
    point_created = sorted(set(desired.point_versions) - set(points))
    point_updated = sorted(
        slug
        for slug in desired.point_slugs & points.keys()
        if points[slug].fixture_managed and (
            points[slug].catalog_version != desired.point_versions.get(slug, points[slug].catalog_version)
            or not points[slug].is_active
            or not points[slug].seo_indexable
            or not _point_matches_catalog(points[slug], slug, desired)
        )
    )
    point_unchanged = sorted((desired.point_slugs & set(points)) - set(point_created) - set(point_updated))
    route_created = sorted(desired.route_slugs - routes.keys())
    route_updated = sorted(
        slug
        for slug in desired.route_slugs & routes.keys()
        if routes[slug].fixture_managed
        and (not routes[slug].is_active or not _route_matches_catalog(routes[slug], slug, desired))
    )
    route_unchanged = sorted((desired.route_slugs & set(routes)) - set(route_created) - set(route_updated))

    conflicts: list[str] = []
    skipped: list[str] = []
    for slug in sorted(desired.point_slugs & points.keys()):
        point = points[slug]
        if not point.fixture_managed and slug not in desired.point_versions:
            skipped.append(f"point {slug}: operator-managed shared reference preserved")
        elif not point.fixture_managed:
            conflicts.append(f"point {slug}: operator-managed slug collision")
    for slug in sorted(desired.point_slugs - points.keys()):
        if slug not in desired.point_versions:
            conflicts.append(f"point {slug}: shared point is missing and cannot be created by this catalog")
    for slug in sorted(desired.route_slugs & routes.keys()):
        if not routes[slug].fixture_managed:
            conflicts.append(f"route {slug}: operator-managed slug collision")

    stale_points: list[dict[str, str]] = []
    for point in WeatherPoint.objects.filter(fixture_managed=True).exclude(slug__in=desired.point_slugs).order_by("slug"):
        reason = _linked_point_conflict(point)
        if reason:
            conflicts.append(f"point {point.slug}: stale fixture row {reason}")
        elif point.is_active:
            stale_points.append({"slug": point.slug, "reason": "fixture-managed and absent from current catalogs"})

    stale_routes: list[dict[str, str]] = []
    for route in Route.objects.filter(fixture_managed=True).exclude(slug__in=desired.route_slugs).order_by("slug"):
        if route.points.filter(fixture_managed=False).exists():
            conflicts.append(f"route {route.slug}: stale fixture row has operator-managed RoutePoints")
        elif route.is_active:
            stale_routes.append({"slug": route.slug, "reason": "fixture-managed and absent from current catalogs"})

    stale_route_points: list[dict[str, str]] = []
    for slug in sorted(desired.route_slugs & routes.keys()):
        route = routes[slug]
        desired_points = desired.route_point_slugs[slug]
        for point in route.points.filter(fixture_managed=True).exclude(slug__in=desired_points).order_by("sort_order", "pk"):
            stale_route_points.append({"route": route.slug, "slug": point.slug, "reason": "fixture-managed and absent from current route catalog"})

    return {
        "points": {"created": point_created, "updated": point_updated, "unchanged": point_unchanged},
        "routes": {"created": route_created, "updated": route_updated, "unchanged": route_unchanged},
        "stale_points": stale_points,
        "stale_routes": stale_routes,
        "stale_route_points": stale_route_points,
        "skipped": skipped,
        "conflicted": sorted(conflicts),
    }


def _count_changes(before_points: dict[str, tuple[Any, ...]], before_routes: dict[str, tuple[Any, ...]], desired: DesiredCatalog) -> dict[str, int]:
    after_points = {point.slug: _point_state(point) for point in WeatherPoint.objects.all()}
    after_routes = {route.slug: _route_state(route) for route in Route.objects.all()}
    point_created = len(set(after_points) - set(before_points))
    route_created = len(set(after_routes) - set(before_routes))
    point_updated = sum(1 for slug in desired.point_slugs & set(before_points) if before_points[slug] != after_points.get(slug))
    route_updated = sum(1 for slug in desired.route_slugs & set(before_routes) if before_routes[slug] != after_routes.get(slug))
    return {
        "created": point_created + route_created,
        "updated": point_updated + route_updated,
        "unchanged": len(desired.point_slugs) + len(desired.route_slugs) - point_created - route_created - point_updated - route_updated,
    }


@transaction.atomic
def apply_sync(desired: DesiredCatalog, plan: dict[str, Any]) -> dict[str, int]:
    if plan["conflicted"]:
        raise ValueError("Catalog sync conflicts:\n- " + "\n- ".join(plan["conflicted"]))
    before_points = {point.slug: _point_state(point) for point in WeatherPoint.objects.all()}
    before_routes = {route.slug: _route_state(route) for route in Route.objects.all()}
    for relative, _data in desired.files:
        # Prune stale fixture-managed RoutePoints while importing each catalog
        # so route normalization never sees an obsolete point with an older
        # cumulative timestamp (which could produce a negative segment). The
        # operator-managed rows are still protected by seed_catalog's guards.
        seed_catalog(catalog_file=relative, prune=True, force_adopt=False, raise_on_conflict=True, rebuild_search=False)
    deleted_route_points = 0
    for item in plan["stale_route_points"]:
        deleted_route_points += Route.objects.get(slug=item["route"]).points.filter(
            slug=item["slug"], fixture_managed=True
        ).delete()[0]
    for item in plan["stale_routes"]:
        route = Route.objects.get(slug=item["slug"])
        deleted_route_points += route.points.filter(fixture_managed=True).delete()[0]
        route.is_active = False
        route.save(update_fields=["is_active", "updated_at"])
    for item in plan["stale_points"]:
        WeatherPoint.objects.filter(slug=item["slug"], fixture_managed=True).update(is_active=False)
    change_counts = _count_changes(before_points, before_routes, desired)
    if plan["stale_routes"] or plan["stale_points"] or plan["stale_route_points"] or change_counts["created"] or change_counts["updated"]:
        rebuild_search_index()
    counts = change_counts
    counts["deactivated"] = len(plan["stale_points"]) + len(plan["stale_routes"])
    counts["deleted"] = deleted_route_points
    counts["skipped"] = len(plan["skipped"])
    counts["conflicted"] = len(plan["conflicted"])
    return counts

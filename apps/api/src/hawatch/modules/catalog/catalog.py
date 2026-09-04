"""Versioned point/route catalog import.

The JSON files are bootstrap input only; the database is the runtime source of
truth.  Import never creates an extra profile entity and never adds an
unspecified point.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import transaction

from hawatch.modules.catalog.identity import metadata_for_point
from hawatch.modules.catalog.search import rebuild_search_index
from hawatch.modules.catalog.validation import format_issues, validate_catalog_document
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint
from hawatch.modules.routes.publish import axis_for_index, normalize_and_publish_route

DEFAULT_CATALOG_FILE = "catalog/tochal_v1.json"


class CatalogImportConflict(Exception):
    def __init__(self, conflicts: list[str]):
        self.conflicts = conflicts
        super().__init__("; ".join(conflicts))


def _catalog_path(relative: str) -> Path:
    fixtures_dir = Path(settings.FIXTURES_DIR).resolve()
    path = (fixtures_dir / relative).resolve()
    if fixtures_dir not in path.parents or not path.is_file():
        raise FileNotFoundError(f"Catalog file is outside fixtures or does not exist: {relative}")
    return path


def load_catalog_file(relative: str = DEFAULT_CATALOG_FILE) -> dict:
    return json.loads(_catalog_path(relative).read_text(encoding="utf-8"))


def _point_slug(data: dict) -> str:
    explicit = data.get("primary_point")
    if explicit:
        return str(explicit)
    for slug, row in data["weather_points"].items():
        if row.get("kind") == "primary":
            return slug
    return next(iter(data["weather_points"]))


def _derive_segments(cumulative: dict[str, int], ordered: list[str]) -> dict[str, int]:
    previous = 0
    segments = {}
    for slug in ordered:
        segments[slug] = cumulative[slug] - previous
        previous = cumulative[slug]
    return segments


def _validate_document_shape(data: dict) -> None:
    for key in ("catalog_version", "point", "weather_points", "routes"):
        if key not in data:
            raise ValueError(f"Catalog is missing required key: {key}")
    if not isinstance(data["point"], dict):
        raise ValueError("point must be an object")
    if not isinstance(data["routes"], dict):
        raise ValueError("routes must be an object")
    points = set(data["weather_points"])
    for slug, row in data["weather_points"].items():
        if not isinstance(row, dict) or not str(row.get("name") or "").strip():
            raise ValueError(f"WeatherPoint {slug}.name is required")
    if _point_slug(data) not in points:
        raise ValueError("primary point does not exist in weather_points")
    shared = set(data.get("shared_weather_points") or [])
    points |= shared
    for key, route in data["routes"].items():
        ordered = route.get("points") or []
        if not ordered or len(ordered) != len(set(ordered)):
            raise ValueError(f"Route {key} must contain unique ordered points")
        missing = sorted(set(ordered) - points)
        if missing:
            raise ValueError(f"Route {key} references missing points: {', '.join(missing)}")
    issues = [issue for issue in validate_catalog_document(data) if issue.level == "error"]
    if issues:
        raise ValueError("Catalog identity validation failed:\n" + format_issues(issues))


def _timing(route_row: dict) -> dict:
    timing = route_row.get("timing") or {}
    status = route_row.get("timing_status", Route.TimingStatus.PENDING)
    if not timing or status == Route.TimingStatus.PENDING:
        return {"status": Route.TimingStatus.PENDING, "one_way": None, "cumulative": {}, "segments": {}, "method": "", "version": "", "confidence": "", "uncertainty": None, "sources": []}
    ordered = list(route_row["points"])
    cumulative = {slug: int(timing["cumulative_minutes"][slug]) for slug in ordered}
    return {
        "status": status,
        "one_way": int(route_row["one_way_minutes"]),
        "cumulative": cumulative,
        "segments": _derive_segments(cumulative, ordered),
        "method": str(timing.get("method") or ""),
        "version": str(timing.get("version") or ""),
        "confidence": str(timing.get("confidence") or ""),
        "uncertainty": timing.get("uncertainty_minutes"),
        "sources": list(timing.get("source_urls") or []),
    }


@transaction.atomic
def seed_catalog(*, catalog: dict | None = None, catalog_file: str | None = None, prune: bool = False, force_adopt: bool = False, raise_on_conflict: bool = False) -> dict:
    if catalog is not None and catalog_file is not None:
        raise ValueError("Pass catalog or catalog_file, not both")
    data = catalog or load_catalog_file(catalog_file or DEFAULT_CATALOG_FILE)
    _validate_document_shape(data)
    version = data["catalog_version"]
    profile = data["point"]
    conflicts: list[str] = []
    points: dict[str, WeatherPoint] = {}
    for slug, row in data["weather_points"].items():
        existing = WeatherPoint.objects.filter(slug=slug).first()
        if existing and not existing.fixture_managed and not force_adopt:
            conflicts.append(f"WeatherPoint slug={slug} is operator-managed; skipped")
            continue
        kind = row.get("kind") or WeatherPoint.Kind.SHARED
        if kind not in {choice for choice, _label in WeatherPoint.Kind.choices}:
            kind = WeatherPoint.Kind.SHARED
        identity = metadata_for_point(slug, row, primary_label=profile.get("name", ""), is_primary=kind == WeatherPoint.Kind.PRIMARY)
        defaults = {
            "name": identity["name"], "page_name": identity["page_name"], "short_label": identity["short_label"], "place_type": identity["place_type"],
            "identity_summary": identity["identity_summary"], "importance": identity["importance"], "name_status": identity["name_status"], "source_urls": identity["source_urls"], "aliases": identity["aliases"],
            "kind": kind, "location": Point(row["longitude"], row["latitude"], srid=4326), "elevation_m": row.get("elevation_m"), "elevation_source": row.get("elevation_source") or "",
            "tile_name": row.get("tile_name") or (profile.get("tile_name", "") if slug == _point_slug(data) else ""), "short_category": row.get("short_category") or (profile.get("short_category", "") if slug == _point_slug(data) else ""),
            "category": row.get("category") or (profile.get("category", "") if slug == _point_slug(data) else ""), "category_key": row.get("category_key") or (profile.get("category_key", "") if slug == _point_slug(data) else ""),
            "region": row.get("region") or (profile.get("region", "") if slug == _point_slug(data) else ""), "image": row.get("image") or (profile.get("image", "") if slug == _point_slug(data) else ""), "image_alt": row.get("image_alt") or (profile.get("image_alt", "") if slug == _point_slug(data) else ""),
            "popular_order": profile.get("popular_order", 0) if slug == _point_slug(data) else 0, "is_popular": bool(profile.get("is_popular", False)) if slug == _point_slug(data) else False, "seo_indexable": bool(profile.get("seo_indexable", kind == WeatherPoint.Kind.PRIMARY)),
            "climate": row.get("climate") or profile.get("climate", "alpine"), "status": row.get("status") or (WeatherPoint.Status.UNRESOLVED_ELEVATION if row.get("elevation_m") is None else WeatherPoint.Status.APPROVED), "provenance": WeatherPoint.Provenance.CURATED,
            "catalog_version": version, "data_mode": "live", "seed_version": version, "ingest_enabled": True, "fixture_managed": True,
        }
        if existing is None:
            defaults["is_active"] = bool(row.get("is_active", profile.get("is_active", True)))
            existing = WeatherPoint.objects.create(slug=slug, **defaults)
        else:
            for key, value in defaults.items(): setattr(existing, key, value)
            existing.save()
        points[slug] = existing
    for slug in data.get("shared_weather_points") or []:
        shared = WeatherPoint.objects.filter(slug=slug, is_active=True).first()
        if shared is None:
            raise ValueError(f"Shared WeatherPoint does not exist: {slug}")
        points[slug] = shared

    kept_routes: list[int] = []
    for catalog_key, row in data["routes"].items():
        ordered = list(row["points"])
        if any(slug not in points for slug in ordered):
            conflicts.append(f"Route {row['slug']} skipped: missing point")
            continue
        timing = _timing(row)
        route, created = Route.objects.get_or_create(slug=row["slug"], defaults={"title": row["title"], "subtitle": row["subtitle"], "trail_label": row["trail_label"], "origin": row["origin"], "target_label": row["target_label"], "region": row["region"], "origin_location": points[ordered[0]].location})
        if not created and not route.fixture_managed and not force_adopt:
            conflicts.append(f"Route slug={route.slug} is operator-managed; skipped")
            kept_routes.append(route.pk)
            continue
        route.title, route.subtitle, route.trail_label, route.origin, route.target_label, route.region = row["title"], row["subtitle"], row["trail_label"], row["origin"], row["target_label"], row["region"]
        route.distance_km, route.ascent_m, route.one_way_minutes = row.get("distance_km"), row.get("ascent_m"), timing["one_way"]
        route.default_start_minutes, route.timing_status, route.timing_method, route.timing_version = row.get("default_start_minutes", 360), timing["status"], timing["method"], timing["version"]
        route.timing_confidence, route.timing_uncertainty_minutes, route.timing_source_urls = timing["confidence"], timing["uncertainty"], timing["sources"]
        route.featured, route.sort_order, route.origin_location, route.origin_weather_point, route.target_weather_point = row.get("featured", False), row.get("sort_order", 0), points[ordered[0]].location, points[ordered[0]], points[ordered[-1]]
        route.catalog_key, route.data_mode, route.seed_version, route.fixture_managed = catalog_key, "live", version, True
        route.save()
        existing = {rp.slug: rp for rp in route.points.all()}
        for index, slug in enumerate(ordered):
            wp = points[slug]
            rp, _ = RoutePoint.objects.get_or_create(route=route, slug=slug, defaults={"weather_point": wp, "name": wp.name, "sort_order": index + 1})
            if not rp.fixture_managed and not force_adopt:
                conflicts.append(f"RoutePoint {route.slug}:{slug} is operator-managed; skipped")
                continue
            x, y = axis_for_index(index, len(ordered))
            values = {"weather_point": wp, "name": wp.name, "elevation_m": wp.elevation_m, "location": wp.location, "base_minutes": timing["cumulative"].get(slug), "segment_minutes": timing["segments"].get(slug), "cumulative_minutes": timing["cumulative"].get(slug), "progress_pct": round(timing["cumulative"].get(slug, 0) / timing["one_way"] * 100, 2) if timing["one_way"] else None, "timing_status": timing["status"] if timing["status"] != Route.TimingStatus.PENDING else RoutePoint.TimingStatus.PENDING, "sort_order": index + 1, "public_note": str((row.get("public_point_notes") or {}).get(slug, ""))[:255], "axis_x": x, "axis_y": y, "data_mode": "live", "seed_version": version, "fixture_managed": True}
            for key, value in values.items(): setattr(rp, key, value)
            rp.save()
        if prune:
            route.points.filter(fixture_managed=True).exclude(slug__in=ordered).delete()
        normalize_and_publish_route(route, rebuild_search=False)
        kept_routes.append(route.pk)
    if prune:
        Route.objects.filter(fixture_managed=True, data_mode="live").exclude(pk__in=kept_routes).delete()
    if raise_on_conflict and conflicts:
        raise CatalogImportConflict(conflicts)
    search = rebuild_search_index()
    return {"catalog_version": version, "point": _point_slug(data), "weather_point_count": len(points), "route_count": len(kept_routes), "shared_point_slugs": sorted(points), "pruned": prune, "conflicts": conflicts, **search}


def bootstrap_live_catalog_if_empty(*, catalog_file: str = DEFAULT_CATALOG_FILE) -> dict | None:
    from hawatch.modules.catalog.runtime import live_catalog_is_empty
    return seed_catalog(catalog_file=catalog_file, prune=False) if live_catalog_is_empty() else None

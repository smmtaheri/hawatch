"""Generic, versioned destination catalog loader and idempotent database seed."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import F

from hawatch.modules.catalog.search import rebuild_search_index
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint

DEFAULT_CATALOG_FILE = "catalog/tochal_v1.json"


def _catalog_path(relative: str) -> Path:
    fixtures_dir = Path(settings.FIXTURES_DIR).resolve()
    path = (fixtures_dir / relative).resolve()
    if fixtures_dir not in path.parents or not path.is_file():
        raise FileNotFoundError(f"Catalog file is outside fixtures or does not exist: {relative}")
    return path


def load_catalog_file(relative: str = DEFAULT_CATALOG_FILE) -> dict:
    return json.loads(_catalog_path(relative).read_text(encoding="utf-8"))


def _axis_for_index(index: int, total: int) -> tuple[int, int]:
    if total <= 1:
        return 50, 50
    x = 12 + round((76 * index) / (total - 1))
    y = 72 - round((44 * index) / (total - 1))
    return x, y


def _destination_point_slug(data: dict) -> str:
    explicit = data.get("destination_weather_point")
    if explicit:
        return explicit
    for slug, row in data["weather_points"].items():
        if row.get("kind") == "destination":
            return slug
    destination_slug = data["destination"]["slug"]
    if destination_slug in data["weather_points"]:
        return destination_slug
    return next(iter(data["weather_points"]))


def _validate_document_shape(data: dict) -> None:
    for key in ("catalog_version", "destination", "weather_points", "routes"):
        if key not in data:
            raise ValueError(f"Catalog is missing required key: {key}")
    if not data["weather_points"]:
        raise ValueError("Catalog must contain at least one weather point")
    point_slugs = set(data["weather_points"])
    destination_slug = _destination_point_slug(data)
    if destination_slug not in point_slugs:
        raise ValueError(f"destination weather point does not exist: {destination_slug}")
    for route_key, route in data["routes"].items():
        points = route.get("points") or []
        if not points:
            raise ValueError(f"Route has no points: {route_key}")
        missing = sorted(set(points) - point_slugs)
        if missing:
            raise ValueError(f"Route {route_key} references missing points: {', '.join(missing)}")


@transaction.atomic
def seed_catalog(*, catalog: dict | None = None, catalog_file: str | None = None) -> dict:
    """Upsert any catalog document and its ordered shared WeatherPoint links.

    A catalog file is the only destination-specific input. Re-running the same
    version is safe and stale curated rows for that destination are removed.
    """
    if catalog is not None and catalog_file is not None:
        raise ValueError("Pass catalog or catalog_file, not both")
    data = catalog or load_catalog_file(catalog_file or DEFAULT_CATALOG_FILE)
    _validate_document_shape(data)

    version = data["catalog_version"]
    dest_row = data["destination"]
    destination = Destination.objects.update_or_create(
        slug=dest_row["slug"],
        defaults={
            "tile_name": dest_row["tile_name"],
            "name": dest_row["name"],
            "short_category": dest_row["short_category"],
            "category": dest_row["category"],
            "category_key": dest_row["category_key"],
            "region": dest_row["region"],
            "elevation_m": dest_row["elevation_m"],
            "location": Point(dest_row["longitude"], dest_row["latitude"], srid=4326),
            "image": dest_row["image"],
            "image_alt": dest_row["image_alt"],
            "popular_order": dest_row["popular_order"],
            "climate": dest_row["climate"],
            "is_popular": dest_row["is_popular"],
            "is_active": dest_row["is_active"],
            "aliases": dest_row.get("aliases") or [],
            "data_mode": "live",
            "seed_version": version,
        },
    )[0]

    weather_points: dict[str, WeatherPoint] = {}
    for slug, row in data["weather_points"].items():
        elevation = row.get("elevation_m")
        kind = row.get("kind") or WeatherPoint.Kind.SHARED
        if kind == "destination":
            kind = WeatherPoint.Kind.DESTINATION
        status = row.get("status")
        if status not in {choice for choice, _label in WeatherPoint.Status.choices}:
            status = (
                WeatherPoint.Status.UNRESOLVED_ELEVATION
                if elevation is None
                else WeatherPoint.Status.APPROVED
            )
        point = WeatherPoint.objects.update_or_create(
            slug=slug,
            defaults={
                "name": row["name"],
                "aliases": row.get("aliases") or [],
                "kind": kind,
                "location": Point(row["longitude"], row["latitude"], srid=4326),
                "elevation_m": elevation,
                "destination": destination,
                "climate": row.get("climate", dest_row["climate"]),
                "status": status,
                "provenance": WeatherPoint.Provenance.CURATED,
                "catalog_version": version,
                "data_mode": "live",
                "seed_version": version,
            },
        )[0]
        weather_points[slug] = point

    destination_point = weather_points[_destination_point_slug(data)]
    WeatherPoint.objects.update_or_create(
        slug=f"dest:{destination.slug}",
        defaults={
            "name": destination.name,
            "kind": WeatherPoint.Kind.DESTINATION,
            "location": destination_point.location,
            "elevation_m": destination_point.elevation_m,
            "destination": destination,
            "climate": destination.climate,
            "status": WeatherPoint.Status.APPROVED,
            "provenance": WeatherPoint.Provenance.CURATED,
            "catalog_version": version,
            "data_mode": "live",
            "seed_version": version,
        },
    )

    kept_route_ids: list[int] = []
    for catalog_key, route_row in data["routes"].items():
        point_slugs = route_row["points"]
        route = Route.objects.update_or_create(
            slug=route_row["slug"],
            defaults={
                "destination": destination,
                "title": route_row["title"],
                "subtitle": route_row["subtitle"],
                "trail_label": route_row["trail_label"],
                "origin": route_row["origin"],
                "destination_label": route_row["destination_label"],
                "region": route_row["region"],
                "distance_km": route_row.get("distance_km"),
                "ascent_m": route_row.get("ascent_m"),
                "round_trip_minutes": route_row.get("round_trip_minutes"),
                "default_start_minutes": route_row.get("default_start_minutes", 360),
                "timing_status": route_row.get("timing_status", Route.TimingStatus.PENDING),
                "featured": route_row.get("featured", False),
                "sort_order": route_row.get("sort_order", 0),
                "origin_location": weather_points[point_slugs[0]].location,
                "catalog_key": catalog_key,
                "data_mode": "live",
                "seed_version": version,
            },
        )[0]
        kept_route_ids.append(route.pk)

        desired_slugs = set(point_slugs)
        RoutePoint.objects.filter(route=route).update(sort_order=F("sort_order") + 1000)
        RoutePoint.objects.filter(route=route).exclude(slug__in=desired_slugs).delete()

        for index, point_slug in enumerate(point_slugs):
            wp = weather_points[point_slug]
            point_row = data["weather_points"][point_slug]
            axis_x, axis_y = _axis_for_index(index, len(point_slugs))
            is_last = index == len(point_slugs) - 1
            RoutePoint.objects.update_or_create(
                route=route,
                slug=point_slug,
                defaults={
                    "weather_point": wp,
                    "destination": destination if is_last else None,
                    "name": wp.name,
                    "elevation_m": wp.elevation_m,
                    "location": wp.location,
                    "base_minutes": point_row.get("base_minutes"),
                    "segment_minutes": point_row.get("segment_minutes"),
                    "cumulative_minutes": point_row.get("cumulative_minutes"),
                    "segment_distance_m": point_row.get("segment_distance_m"),
                    "progress_pct": point_row.get("progress_pct"),
                    "timing_status": point_row.get("timing_status", RoutePoint.TimingStatus.PENDING),
                    "sort_order": index + 1,
                    "note": point_row.get("note", ""),
                    "axis_x": axis_x,
                    "axis_y": axis_y,
                    "data_mode": "live",
                    "seed_version": version,
                },
            )

    stale_routes = Route.objects.filter(destination=destination).exclude(pk__in=kept_route_ids)
    for route in stale_routes:
        RoutePoint.objects.filter(route=route).delete()
        route.delete()

    keep_point_slugs = {*weather_points, f"dest:{destination.slug}"}
    WeatherPoint.objects.filter(
        destination=destination,
        provenance__in=[WeatherPoint.Provenance.DEMO_FIXTURE, WeatherPoint.Provenance.CURATED],
        data_mode="live",
    ).exclude(slug__in=keep_point_slugs).delete()

    return {
        "catalog_version": version,
        "destination": destination.slug,
        "weather_point_count": len(weather_points),
        "route_count": len(kept_route_ids),
        "shared_point_slugs": sorted(weather_points),
        **rebuild_search_index(),
    }

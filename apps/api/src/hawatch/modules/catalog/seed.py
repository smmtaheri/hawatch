from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import F
from django.utils import timezone as dj_timezone

from hawatch.common.time import ALL_HOURS, day_window, hour_bucket, localize_dt, now_tehran
from hawatch.integrations.weather.demo import generate_reading
from hawatch.modules.catalog.search import rebuild_search_index
from hawatch.modules.catalog.tochal import TOCHAL_ROUTE_SLUGS, seed_tochal_catalog
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import DemoSeedState, ForecastRecord, WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint

DATA_MODE = "demo"
logger = logging.getLogger(__name__)

# Same explicit mappings as destinations.0004 backfill (Destination.slug → WeatherPoint.slug).
KNOWN_DESTINATION_WEATHER_POINT_SLUGS = {
    "touchal": "tochal_summit",
}


def _is_proven_destination_canonical(point: WeatherPoint | None, destination: Destination) -> bool:
    """True only when ownership/type prove the point is this destination's canonical place."""
    if point is None:
        return False
    if str(point.slug).startswith("dest:"):
        return False
    return point.destination_id == destination.id and point.kind == WeatherPoint.Kind.DESTINATION


def _ensure_destination_weather_point(destination: Destination, seed_version: str) -> WeatherPoint | None:
    """
    Attach or refresh the destination's canonical WeatherPoint safely.

    Never overwrite an unrelated WeatherPoint that merely shares Destination.slug.
    On ambiguous slug collision, leave Destination.weather_point unresolved and log.
    """
    mapped_slug = KNOWN_DESTINATION_WEATHER_POINT_SLUGS.get(destination.slug)
    desired_slug = mapped_slug or destination.slug

    existing = WeatherPoint.objects.filter(slug=desired_slug).first()
    can_reuse = False
    if existing is not None:
        if mapped_slug and existing.slug == mapped_slug:
            can_reuse = True
        elif _is_proven_destination_canonical(existing, destination):
            can_reuse = True
        elif destination.weather_point_id and existing.id == destination.weather_point_id:
            # Already linked as the profile point — only refresh if still destination-kind.
            can_reuse = existing.kind == WeatherPoint.Kind.DESTINATION

    if existing is not None and not can_reuse:
        logger.error(
            "Catalog seed skipped Destination.weather_point for slug=%r: "
            "WeatherPoint slug=%r kind=%r destination_id=%r is not a proven canonical "
            "point for this destination. Map explicitly in catalog/seed "
            "(KNOWN_DESTINATION_WEATHER_POINT_SLUGS) or rename the conflicting point; "
            "refusing to mutate coordinates/forecast ownership.",
            destination.slug,
            existing.slug,
            existing.kind,
            existing.destination_id,
        )
        if destination.weather_point_id == existing.id:
            destination.weather_point = None
            destination.save(update_fields=["weather_point"])
        return None

    defaults = {
        "name": destination.name,
        "kind": WeatherPoint.Kind.DESTINATION,
        "location": destination.location,
        "elevation_m": destination.elevation_m,
        "destination": destination,
        "climate": destination.climate,
        "status": WeatherPoint.Status.APPROVED,
        "provenance": WeatherPoint.Provenance.DEMO_FIXTURE,
        "catalog_version": "",
        "data_mode": DATA_MODE,
        "seed_version": seed_version,
    }
    if existing is None:
        weather_point = WeatherPoint.objects.create(slug=desired_slug, **defaults)
    else:
        for field, value in defaults.items():
            setattr(existing, field, value)
        existing.save(update_fields=list(defaults.keys()))
        weather_point = existing

    if destination.weather_point_id != weather_point.id:
        destination.weather_point = weather_point
        destination.save(update_fields=["weather_point"])
    return weather_point


def _load(relative: str):
    path = Path(settings.FIXTURES_DIR) / relative
    return json.loads(path.read_text(encoding="utf-8"))


def interpolate_point(origin: Point, dest: Point, t: float) -> Point:
    t = min(1.0, max(0.0, t))
    return Point(origin.x + (dest.x - origin.x) * t, origin.y + (dest.y - origin.y) * t, srid=4326)


def ensure_catalog(seed_version: str) -> dict[str, Destination]:
    destinations = {}
    for item in _load("destinations/destinations.json"):
        location = Point(item["longitude"], item["latitude"], srid=4326)
        obj, _ = Destination.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "tile_name": item["tile_name"],
                "name": item["name"],
                "short_category": item["short_category"],
                "category": item["category"],
                "category_key": item["category_key"],
                "region": item["region"],
                "elevation_m": item["elevation_m"],
                "location": location,
                "image": item["image"],
                "image_alt": item["image_alt"],
                "popular_order": item["popular_order"],
                "climate": item["climate"],
                "is_popular": item["is_popular"],
                "is_active": item["is_active"],
                "data_mode": DATA_MODE,
                "seed_version": seed_version,
            },
        )
        destinations[obj.slug] = obj
        if obj.slug == "touchal":
            # Tochal destination weather point comes from the curated catalog seed.
            continue
        # Canonical WeatherPoint — never adopt an unrelated slug collision.
        _ensure_destination_weather_point(obj, seed_version)

    routes_by_slug = {}
    for item in _load("routes/routes.json"):
        if item["slug"] in TOCHAL_ROUTE_SLUGS:
            continue
        destination = destinations[item["destination_slug"]]
        origin = Point(item["origin_longitude"], item["origin_latitude"], srid=4326)
        obj, _ = Route.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "destination": destination,
                "title": item["title"],
                "subtitle": item["subtitle"],
                "trail_label": item["trail_label"],
                "origin": item["origin"],
                "destination_label": item["destination_label"],
                "region": item["region"],
                "distance_km": item["distance_km"],
                "ascent_m": item["ascent_m"],
                "round_trip_minutes": item["round_trip_minutes"],
                "default_start_minutes": item["default_start_minutes"],
                "timing_status": Route.TimingStatus.ESTIMATED,
                "featured": item["featured"],
                "sort_order": item["sort_order"],
                "origin_location": origin,
                "catalog_key": "",
                "data_mode": DATA_MODE,
                "seed_version": seed_version,
            },
        )
        routes_by_slug[obj.slug] = obj
        # origin/target WeatherPoints are set after route points are linked below.

    point_rows = [item for item in _load("route_points/route_points.json") if item["route_slug"] not in TOCHAL_ROUTE_SLUGS]
    counts: dict[str, int] = {}
    for item in point_rows:
        counts[item["route_slug"]] = counts.get(item["route_slug"], 0) + 1

    # Avoid unique(route, sort_order) collisions when an existing catalog
    # changes point order. Every current order stays unique while the final
    # orders are written below.
    for route in routes_by_slug.values():
        RoutePoint.objects.filter(route=route).update(sort_order=F("sort_order") + 1000)

    for item in point_rows:
        route = routes_by_slug[item["route_slug"]]
        count = counts[item["route_slug"]]
        t = (item["sort_order"] - 1) / max(1, count - 1)
        location = interpolate_point(route.origin_location, route.destination.location, t)
        linked = route.destination if item["sort_order"] == count else None
        point, _ = RoutePoint.objects.update_or_create(
            route=route,
            slug=item["slug"],
            defaults={
                "destination": linked,
                "name": item["name"],
                "elevation_m": item["elevation_m"],
                "location": location,
                "base_minutes": item["base_minutes"],
                "segment_minutes": None,
                "cumulative_minutes": item["base_minutes"],
                "segment_distance_m": None,
                "progress_pct": None,
                "timing_status": RoutePoint.TimingStatus.ESTIMATED,
                "sort_order": item["sort_order"],
                "note": item["note"],
                "axis_x": item["axis_x"],
                "axis_y": item["axis_y"],
                "data_mode": DATA_MODE,
                "seed_version": seed_version,
            },
        )
        weather_point, _ = WeatherPoint.objects.update_or_create(
            slug=f"route:{route.slug}:{point.slug}",
            defaults={
                "name": point.name,
                "kind": WeatherPoint.Kind.ROUTE_POINT,
                "location": point.location,
                "elevation_m": point.elevation_m,
                "destination": route.destination,
                "climate": route.destination.climate,
                "status": WeatherPoint.Status.APPROVED,
                "provenance": WeatherPoint.Provenance.DEMO_FIXTURE,
                "catalog_version": "",
                "data_mode": DATA_MODE,
                "seed_version": seed_version,
            },
        )
        if point.weather_point_id != weather_point.id:
            point.weather_point = weather_point
            point.save(update_fields=["weather_point"])

    for route in routes_by_slug.values():
        ordered = list(
            RoutePoint.objects.filter(route=route)
            .exclude(weather_point=None)
            .order_by("sort_order")
            .select_related("weather_point")
        )
        if not ordered:
            continue
        updates = []
        if route.origin_weather_point_id != ordered[0].weather_point_id:
            route.origin_weather_point = ordered[0].weather_point
            updates.append("origin_weather_point")
        if route.target_weather_point_id != ordered[-1].weather_point_id:
            route.target_weather_point = ordered[-1].weather_point
            updates.append("target_weather_point")
        if updates:
            route.save(update_fields=updates)

    # Curated Tochal catalog replaces fixture Tochal routes/points and shares weather points.
    seed_tochal_catalog()
    rebuild_search_index()
    return destinations


def ensure_forecasts(seed_version: str, *, force: bool = False) -> DemoSeedState:
    local = now_tehran()
    bucket = hour_bucket(local)
    today = local.date()
    state, created = DemoSeedState.objects.get_or_create(
        key="demo",
        defaults={
            "seed_version": seed_version,
            "last_hour_bucket": "",
            "generated_at": dj_timezone.now(),
            "local_date": today,
            "local_hour": local.hour,
        },
    )
    if not force and not created and state.last_hour_bucket == bucket and state.seed_version == seed_version:
        return state

    generated_at = dj_timezone.now()
    dates = day_window(today)
    records = []
    for weather_point in WeatherPoint.objects.select_related("destination").all():
        elevation = weather_point.elevation_m
        if elevation is None:
            elevation = weather_point.destination.elevation_m if weather_point.destination_id else 2000
        for day in dates:
            for hour in ALL_HOURS:
                reading = generate_reading(
                    point_slug=weather_point.slug,
                    climate_key=weather_point.climate,
                    elevation_m=elevation,
                    local_date=day,
                    hour=hour,
                )
                forecast_at = localize_dt(day, hour)
                records.append(
                    ForecastRecord(
                        weather_point=weather_point,
                        snapshot=None,
                        forecast_at=forecast_at,
                        valid_from=forecast_at,
                        valid_to=forecast_at + timedelta(hours=2),
                        generated_at=generated_at,
                        hour_bucket=bucket,
                        temperature_c=reading["temperature_c"],
                        apparent_temperature_c=reading["apparent_temperature_c"],
                        weather_code=reading["weather_code"],
                        condition_label=reading["condition_label"],
                        icon=reading["icon"],
                        wind_speed_kmh=reading["wind_speed_kmh"],
                        wind_gust_kmh=reading["wind_gust_kmh"],
                        wind_direction_deg=reading["wind_direction_deg"],
                        precipitation_probability=reading["precipitation_probability"],
                        precipitation_mm=reading["precipitation_mm"],
                        snowfall_cm=None,
                        visibility_km=reading["visibility_km"],
                        cloud_cover_pct=reading["cloud_cover_pct"],
                        uv_index=reading["uv_index"],
                        freezing_level_m=reading["freezing_level_m"],
                        cloud_base_m=reading["cloud_base_m"],
                        severity=reading["severity"],
                        freshness=ForecastRecord.Freshness.READY,
                        data_mode=DATA_MODE,
                        source="hawatch-demo",
                        seed_version=seed_version,
                        provider="demo",
                    )
                )

    with transaction.atomic():
        ForecastRecord.objects.filter(seed_version=seed_version, data_mode=DATA_MODE).delete()
        ForecastRecord.objects.bulk_create(records, batch_size=500)
        state.seed_version = seed_version
        state.last_hour_bucket = bucket
        state.generated_at = generated_at
        state.local_date = today
        state.local_hour = local.hour
        state.save()
    return state


def seed_demo_data(*, force: bool = False) -> DemoSeedState:
    if not settings.DEMO_DATA_ENABLED:
        state = DemoSeedState.objects.filter(key="demo").first()
        return state
    seed_version = settings.DEMO_SEED_VERSION
    ensure_catalog(seed_version)
    return ensure_forecasts(seed_version, force=force)


def refresh_if_bucket_changed() -> DemoSeedState | None:
    if not settings.DEMO_DATA_ENABLED:
        return None
    return seed_demo_data(force=False)

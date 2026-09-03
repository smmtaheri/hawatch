"""Generic, versioned destination catalog loader and idempotent database seed."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import Q

from hawatch.modules.catalog.search import rebuild_search_index
from hawatch.modules.catalog.identity import metadata_for_point
from hawatch.modules.catalog.validation import format_issues, validate_catalog_document
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint
from hawatch.modules.routes.publish import (
    axis_for_index,
    normalize_and_publish_route,
    shift_route_point_sort_orders,
)

DEFAULT_CATALOG_FILE = "catalog/tochal_v1.json"
TIMING_CONFIDENCE_VALUES = {"high", "medium", "low"}
TIMING_STATUS_VALUES = {choice for choice, _label in Route.TimingStatus.choices}
WEATHER_POINT_NAME_MAX_LENGTH = 80
WEATHER_POINT_ELEVATION_SOURCE_MAX_LENGTH = 255


class CatalogImportConflict(Exception):
    """Raised when force_adopt=False and conflicts cannot be skipped safely."""

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


def _axis_for_index(index: int, total: int) -> tuple[int, int]:
    return axis_for_index(index, total)


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


def _derive_segment_minutes(cumulative: dict[str, int], ordered_slugs: list[str]) -> dict[str, int]:
    segments: dict[str, int] = {}
    previous = 0
    for slug in ordered_slugs:
        value = cumulative[slug]
        segments[slug] = value - previous
        previous = value
    return segments


def _restore_manual_route_point_positions(
    *,
    route: Route,
    fixture_point_slugs: list[str],
    manual_positions: list[tuple[int, int]],
) -> None:
    """Merge manual points into a refreshed fixture route without moving them to the end.

    A catalog refresh owns the relative order of fixture-managed points.  An
    operator-managed RoutePoint keeps its previous ordinal slot: a manual point
    at slot ``2`` is placed between fixture points 1 and 2, while a point after
    the fixture range remains at the end.  This makes ordinary imports safe for
    routes that have been extended from Admin.
    """
    fixture_points = {
        point.slug: point
        for point in RoutePoint.objects.filter(route=route, slug__in=fixture_point_slugs)
    }
    ordered_fixtures = [fixture_points[slug] for slug in fixture_point_slugs]
    manual_points = {
        point.pk: point
        for point in RoutePoint.objects.filter(route=route, fixture_managed=False)
    }

    # Shift every row first so assigning dense orders cannot violate the unique
    # (route, sort_order) constraint.
    shift_route_point_sort_orders(route)

    manual_by_slot: dict[int, list[RoutePoint]] = {}
    for point_id, original_order in manual_positions:
        point = manual_points.get(point_id)
        if point is not None:
            manual_by_slot.setdefault(max(1, original_order), []).append(point)

    combined: list[RoutePoint] = []
    for fixture_index, fixture_point in enumerate(ordered_fixtures, start=1):
        combined.extend(manual_by_slot.pop(fixture_index, []))
        combined.append(fixture_point)
    for slot in sorted(manual_by_slot):
        combined.extend(manual_by_slot[slot])

    for index, point in enumerate(combined, start=1):
        RoutePoint.objects.filter(pk=point.pk).update(sort_order=index)


def _validate_route_timing(route_key: str, route: dict, point_slugs: set[str]) -> None:
    """Validate optional route timing block; incomplete/ambiguous data must stay pending."""
    timing = route.get("timing")
    status = route.get("timing_status", Route.TimingStatus.PENDING)
    if status not in TIMING_STATUS_VALUES:
        raise ValueError(f"Route {route_key} has invalid timing_status: {status}")
    if timing is None:
        if status != Route.TimingStatus.PENDING:
            raise ValueError(f"Route {route_key} has timing_status={status} but no timing block")
        return

    ordered = list(route.get("points") or [])
    if len(ordered) != len(set(ordered)):
        raise ValueError(f"Route {route_key} has duplicate point slugs")

    cumulative = timing.get("cumulative_minutes")
    if not isinstance(cumulative, dict) or not cumulative:
        raise ValueError(f"Route {route_key} timing.cumulative_minutes is required when timing is present")

    missing = sorted(set(cumulative) - point_slugs)
    if missing:
        raise ValueError(f"Route {route_key} timing references missing weather points: {', '.join(missing)}")
    extra = sorted(set(cumulative) - set(ordered))
    if extra:
        raise ValueError(f"Route {route_key} timing includes points not on the route: {', '.join(extra)}")
    absent = sorted(set(ordered) - set(cumulative))
    if absent:
        raise ValueError(f"Route {route_key} timing missing cumulative entries: {', '.join(absent)}")

    values = [int(cumulative[slug]) for slug in ordered]
    if values[0] != 0:
        raise ValueError(f"Route {route_key} first cumulative_minutes must be 0")
    for index in range(1, len(values)):
        if values[index] <= values[index - 1]:
            raise ValueError(
                f"Route {route_key} cumulative_minutes must be strictly monotonic "
                f"({ordered[index - 1]}={values[index - 1]} → {ordered[index]}={values[index]})"
            )

    one_way = route.get("one_way_minutes")
    if one_way is None:
        raise ValueError(f"Route {route_key} one_way_minutes is required when timing is present")
    if int(one_way) != values[-1]:
        raise ValueError(
            f"Route {route_key} one_way_minutes ({one_way}) must equal final cumulative ({values[-1]})"
        )
    if route.get("round_trip_minutes") is not None:
        raise ValueError(
            f"Route {route_key} must not set round_trip_minutes for one-way ascent timing; use one_way_minutes"
        )

    segments = timing.get("segment_minutes")
    derived = _derive_segment_minutes({slug: int(cumulative[slug]) for slug in ordered}, ordered)
    if segments is not None:
        if set(segments) != set(ordered):
            raise ValueError(f"Route {route_key} segment_minutes keys must match route points")
        for slug in ordered:
            if int(segments[slug]) != derived[slug]:
                raise ValueError(
                    f"Route {route_key} segment_minutes[{slug}]={segments[slug]} "
                    f"!= cumulative difference {derived[slug]}"
                )

    if status == Route.TimingStatus.PENDING:
        raise ValueError(f"Route {route_key} has a timing block but timing_status=pending")

    # estimated/curated require complete provenance; pending stays permissive (no timing block).
    method = str(timing.get("method") or "").strip()
    if not method:
        raise ValueError(f"Route {route_key} timing.method is required for {status}")
    version = str(timing.get("version") or "").strip()
    if not version:
        raise ValueError(f"Route {route_key} timing.version is required for {status}")
    confidence = str(timing.get("confidence") or "").strip()
    if confidence not in TIMING_CONFIDENCE_VALUES:
        raise ValueError(
            f"Route {route_key} timing.confidence must be one of "
            f"{sorted(TIMING_CONFIDENCE_VALUES)} for {status}"
        )
    uncertainty = timing.get("uncertainty_minutes")
    if uncertainty is None:
        raise ValueError(f"Route {route_key} timing.uncertainty_minutes is required for {status}")
    try:
        uncertainty_int = int(uncertainty)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Route {route_key} timing.uncertainty_minutes must be an integer") from exc
    if uncertainty_int < 0:
        raise ValueError(f"Route {route_key} timing.uncertainty_minutes must be >= 0")
    sources = timing.get("source_urls")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"Route {route_key} timing.source_urls must be a non-empty list for {status}")
    if not all(isinstance(url, str) and url.strip() for url in sources):
        raise ValueError(f"Route {route_key} timing.source_urls must contain non-empty URL strings")


def _validate_document_shape(data: dict) -> None:
    for key in ("catalog_version", "destination", "weather_points", "routes"):
        if key not in data:
            raise ValueError(f"Catalog is missing required key: {key}")
    if not data["weather_points"]:
        raise ValueError("Catalog must contain at least one weather point")
    destination = data["destination"]
    if not isinstance(destination, dict):
        raise ValueError("destination must be an object")
    if not isinstance(data["routes"], dict):
        raise ValueError("routes must be an object; use {} when no route is curated")
    for key in ("slug", "tile_name", "name", "short_category", "category", "category_key", "region", "climate"):
        if not str(destination.get(key) or "").strip():
            raise ValueError(f"destination.{key} is required")
    point_slugs = set(data["weather_points"])
    shared_weather_points = data.get("shared_weather_points") or []
    if not isinstance(shared_weather_points, list) or not all(
        isinstance(slug, str) and slug.strip() for slug in shared_weather_points
    ):
        raise ValueError("shared_weather_points must be a list of non-empty slugs")
    if len(shared_weather_points) != len(set(shared_weather_points)):
        raise ValueError("shared_weather_points must not contain duplicate slugs")
    shared_slugs = set(shared_weather_points)
    overlap = sorted(point_slugs & shared_slugs)
    if overlap:
        raise ValueError(
            "shared_weather_points must not repeat local weather points: "
            + ", ".join(overlap)
        )
    point_slugs |= shared_slugs
    for point_slug, point in data["weather_points"].items():
        if not isinstance(point, dict):
            raise ValueError(f"WeatherPoint {point_slug} must be an object")
        name = point.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"WeatherPoint {point_slug}.name is required")
        if len(name) > WEATHER_POINT_NAME_MAX_LENGTH:
            raise ValueError(
                f"WeatherPoint {point_slug}.name must be at most "
                f"{WEATHER_POINT_NAME_MAX_LENGTH} characters"
            )
        elevation_source = point.get("elevation_source") or ""
        if not isinstance(elevation_source, str):
            raise ValueError(f"WeatherPoint {point_slug}.elevation_source must be a string")
        if len(elevation_source) > WEATHER_POINT_ELEVATION_SOURCE_MAX_LENGTH:
            raise ValueError(
                f"WeatherPoint {point_slug}.elevation_source must be at most "
                f"{WEATHER_POINT_ELEVATION_SOURCE_MAX_LENGTH} characters"
            )
    destination_slug = _destination_point_slug(data)
    if destination_slug not in point_slugs:
        raise ValueError(f"destination weather point does not exist: {destination_slug}")
    for route_key, route in data["routes"].items():
        points = route.get("points") or []
        if not points:
            raise ValueError(f"Route has no points: {route_key}")
        if len(points) != len(set(points)):
            raise ValueError(f"Route {route_key} has duplicate point slugs")
        missing = sorted(set(points) - point_slugs)
        if missing:
            raise ValueError(f"Route {route_key} references missing points: {', '.join(missing)}")
        public_notes = route.get("public_point_notes") or {}
        if not isinstance(public_notes, dict):
            raise ValueError(f"Route {route_key} public_point_notes must be an object")
        unknown_note_slugs = sorted(set(public_notes) - set(points))
        if unknown_note_slugs:
            raise ValueError(
                f"Route {route_key} public_point_notes references points outside the route: "
                f"{', '.join(unknown_note_slugs)}"
            )
        if not all(isinstance(note, str) for note in public_notes.values()):
            raise ValueError(f"Route {route_key} public_point_notes values must be strings")
        _validate_route_timing(route_key, route, point_slugs)

    identity_issues = validate_catalog_document(data)
    errors = [issue for issue in identity_issues if issue.level == "error"]
    if errors:
        raise ValueError("Catalog identity validation failed:\n" + format_issues(errors))


def _route_timing_defaults(route_row: dict) -> dict:
    timing = route_row.get("timing") or {}
    status = route_row.get("timing_status", Route.TimingStatus.PENDING)
    if not timing or status == Route.TimingStatus.PENDING:
        return {
            "timing_status": Route.TimingStatus.PENDING,
            "one_way_minutes": None,
            "timing_method": "",
            "timing_version": "",
            "timing_confidence": "",
            "timing_uncertainty_minutes": None,
            "timing_source_urls": [],
            "point_cumulative": {},
            "point_segments": {},
            "point_timing_status": RoutePoint.TimingStatus.PENDING,
        }
    ordered = list(route_row["points"])
    cumulative = {slug: int(timing["cumulative_minutes"][slug]) for slug in ordered}
    segments = _derive_segment_minutes(cumulative, ordered)
    return {
        "timing_status": status,
        "one_way_minutes": int(route_row["one_way_minutes"]),
        "timing_method": str(timing.get("method") or ""),
        "timing_version": str(timing.get("version") or ""),
        "timing_confidence": str(timing.get("confidence") or ""),
        "timing_uncertainty_minutes": timing.get("uncertainty_minutes"),
        "timing_source_urls": list(timing.get("source_urls") or []),
        "point_cumulative": cumulative,
        "point_segments": segments,
        "point_timing_status": status,
    }


@transaction.atomic
def seed_catalog(
    *,
    catalog: dict | None = None,
    catalog_file: str | None = None,
    prune: bool = False,
    force_adopt: bool = False,
    raise_on_conflict: bool = False,
) -> dict:
    """Upsert a catalog document into the database (non-destructive by default).

    JSON fixtures are bootstrap/import artifacts only. The database is runtime
    source of truth. Manual (non-fixture_managed) rows survive import.

    Without ``force_adopt``, slug collisions with operator-managed rows are
    reported and skipped (never silently overwritten).

    Pruning is opt-in via ``prune=True`` / ``--prune`` and only removes
    ``fixture_managed`` rows for the destination that are absent from the JSON.
    Prune never runs automatically at API startup. Fixture-managed WeatherPoints
    still referenced by manual records are skipped and reported.
    """
    if catalog is not None and catalog_file is not None:
        raise ValueError("Pass catalog or catalog_file, not both")
    data = catalog or load_catalog_file(catalog_file or DEFAULT_CATALOG_FILE)
    _validate_document_shape(data)

    version = data["catalog_version"]
    dest_row = data["destination"]
    conflicts: list[str] = []
    existing_destination = Destination.objects.filter(slug=dest_row["slug"]).first()
    dest_defaults = {
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
        "aliases": dest_row.get("aliases") or [],
        "data_mode": "live",
        "seed_version": version,
    }
    if existing_destination is None:
        dest_defaults["is_active"] = dest_row["is_active"]
        destination = Destination.objects.create(slug=dest_row["slug"], **dest_defaults)
    else:
        for key, value in dest_defaults.items():
            setattr(existing_destination, key, value)
        existing_destination.save()
        destination = existing_destination

    weather_points: dict[str, WeatherPoint] = {}
    skipped_weather_point_slugs: set[str] = set()
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
        identity = metadata_for_point(
            slug,
            row,
            destination_label=dest_row["name"],
            is_destination=kind == WeatherPoint.Kind.DESTINATION,
        )
        defaults = {
            "name": identity["name"],
            "page_name": identity["page_name"],
            "short_label": identity["short_label"],
            "place_type": identity["place_type"],
            "identity_summary": identity["identity_summary"],
            "importance": identity["importance"],
            "name_status": identity["name_status"],
            "source_urls": identity["source_urls"],
            "aliases": identity["aliases"],
            "kind": kind,
            "location": Point(row["longitude"], row["latitude"], srid=4326),
            "elevation_m": elevation,
            "elevation_source": row.get("elevation_source") or "",
            "destination": destination,
            "climate": row.get("climate", dest_row["climate"]),
            "status": status,
            "provenance": WeatherPoint.Provenance.CURATED,
            "catalog_version": version,
            "data_mode": "live",
            "seed_version": version,
            "ingest_enabled": True,
            "fixture_managed": True,
        }
        existing = WeatherPoint.objects.filter(slug=slug).first()
        if existing is not None and not existing.fixture_managed and not force_adopt:
            conflicts.append(
                f"WeatherPoint slug={slug} exists as operator-managed; skipped "
                "(pass force_adopt to overwrite)"
            )
            # Do not use an operator-managed collision as a substitute for the
            # fixture row.  Doing so could silently rewire a destination or a
            # fixture route to an unrelated manually maintained point.
            skipped_weather_point_slugs.add(slug)
            continue
        if existing is None:
            defaults["is_active"] = True
            point = WeatherPoint.objects.create(slug=slug, **defaults)
            weather_points[slug] = point
            continue
        if not existing.fixture_managed and force_adopt:
            existing.fixture_managed = True
        # Preserve operator is_active on refresh/re-import for existing fixture rows.
        for key, value in defaults.items():
            setattr(existing, key, value)
        existing.save()
        weather_points[slug] = existing

    # A route may begin at a canonical WeatherPoint owned by another catalog,
    # for example a mountain route that starts at an already-published lake
    # destination. Shared references are resolved from the database and are
    # never re-owned or overwritten by this catalog import.
    for slug in data.get("shared_weather_points") or []:
        shared_point = WeatherPoint.objects.filter(slug=slug).first()
        if shared_point is None:
            raise ValueError(f"Shared WeatherPoint does not exist: {slug}")
        if not shared_point.is_active or shared_point.data_mode != "live":
            raise ValueError(
                f"Shared WeatherPoint must be active and live: {slug}"
            )
        weather_points[slug] = shared_point

    destination_point_slug = _destination_point_slug(data)
    destination_point = weather_points.get(destination_point_slug)
    # Canonical profile link — do not create synthetic dest:{slug} WeatherPoints.
    if destination_point is None:
        conflicts.append(
            f"Destination slug={destination.slug} weather point={destination_point_slug} "
            "is operator-managed; profile link unchanged"
        )
    elif destination.weather_point_id != destination_point.id:
        destination.weather_point = destination_point
        destination.save(update_fields=["weather_point"])

    kept_route_ids: list[int] = []
    for catalog_key, route_row in data["routes"].items():
        point_slugs = route_row["points"]
        public_notes = route_row.get("public_point_notes") or {}
        if any(slug not in weather_points for slug in point_slugs):
            existing_route = Route.objects.filter(slug=route_row["slug"]).first()
            if existing_route is not None:
                kept_route_ids.append(existing_route.pk)
            conflicting_slugs = sorted(set(point_slugs) & skipped_weather_point_slugs)
            detail = f" ({', '.join(conflicting_slugs)})" if conflicting_slugs else ""
            conflicts.append(
                f"Route {route_row['slug']} skipped: missing weather points after conflicts{detail}"
            )
            continue
        origin_wp = weather_points[point_slugs[0]]
        target_wp = weather_points[point_slugs[-1]]
        timing = _route_timing_defaults(route_row)
        total = timing["one_way_minutes"]
        route_defaults = {
            "destination": destination,
            "title": route_row["title"],
            "subtitle": route_row["subtitle"],
            "trail_label": route_row["trail_label"],
            "origin": route_row["origin"],
            "destination_label": route_row["destination_label"],
            "region": route_row["region"],
            "distance_km": route_row.get("distance_km"),
            "ascent_m": route_row.get("ascent_m"),
            "round_trip_minutes": None,
            "one_way_minutes": timing["one_way_minutes"],
            "default_start_minutes": route_row.get("default_start_minutes", 360),
            "timing_status": timing["timing_status"],
            "timing_method": timing["timing_method"],
            "timing_version": timing["timing_version"],
            "timing_confidence": timing["timing_confidence"],
            "timing_uncertainty_minutes": timing["timing_uncertainty_minutes"],
            "timing_source_urls": timing["timing_source_urls"],
            "featured": route_row.get("featured", False),
            "sort_order": route_row.get("sort_order", 0),
            "origin_location": origin_wp.location,
            "origin_weather_point": origin_wp,
            "target_weather_point": target_wp,
            "catalog_key": catalog_key,
            "data_mode": "live",
            "seed_version": version,
            "fixture_managed": True,
        }
        existing_route = Route.objects.filter(slug=route_row["slug"]).first()
        if existing_route is not None and not existing_route.fixture_managed and not force_adopt:
            conflicts.append(
                f"Route slug={route_row['slug']} exists as operator-managed; skipped "
                "(pass force_adopt to overwrite)"
            )
            kept_route_ids.append(existing_route.pk)
            continue
        if existing_route is None:
            route_defaults["is_active"] = True
            route = Route.objects.create(slug=route_row["slug"], **route_defaults)
        else:
            if not existing_route.fixture_managed and force_adopt:
                existing_route.fixture_managed = True
            for key, value in route_defaults.items():
                setattr(existing_route, key, value)
            existing_route.save()
            route = existing_route
        kept_route_ids.append(route.pk)

        desired_slugs = set(point_slugs)
        manual_positions = list(
            RoutePoint.objects.filter(route=route, fixture_managed=False)
            .order_by("sort_order", "pk")
            .values_list("pk", "sort_order")
        )
        manual_slug_collisions = set(
            RoutePoint.objects.filter(route=route, fixture_managed=False, slug__in=desired_slugs).values_list(
                "slug", flat=True
            )
        )
        if manual_slug_collisions and not force_adopt:
            conflicts.append(
                f"Route {route.slug} skipped: operator-managed RoutePoint slug collision "
                f"({', '.join(sorted(manual_slug_collisions))})"
            )
            continue
        # Free the dense fixture slots before assigning the imported ordering.
        # Manual rows are restored to their original ordinal slots below.
        shift_route_point_sort_orders(route)

        for index, point_slug in enumerate(point_slugs):
            wp = weather_points[point_slug]
            # Shared WeatherPoints intentionally have no duplicate local row;
            # route-specific evidence belongs to the route block itself.
            point_row = data["weather_points"].get(point_slug) or {}
            axis_x, axis_y = _axis_for_index(index, len(point_slugs))
            is_last = index == len(point_slugs) - 1
            cumulative = timing["point_cumulative"].get(point_slug)
            segment = timing["point_segments"].get(point_slug)
            progress = None
            if cumulative is not None and total:
                progress = round((cumulative / total) * 100, 2)
            # Evidence belongs to the internal audit trail. Public route copy
            # must be explicitly supplied by the route, never inherited from a
            # WeatherPoint's research/provenance metadata.
            internal_note = str(point_row.get("evidence_note", "") or "")[:255]
            public_note = str(public_notes.get(point_slug, "") or "")[:255]
            rp_defaults = {
                "weather_point": wp,
                "destination": destination if is_last else None,
                "name": wp.name,
                "elevation_m": wp.elevation_m,
                "location": wp.location,
                "base_minutes": cumulative,
                "segment_minutes": segment,
                "cumulative_minutes": cumulative,
                "segment_distance_m": point_row.get("segment_distance_m"),
                "progress_pct": progress,
                "timing_status": timing["point_timing_status"],
                "sort_order": index + 1,
                "internal_note": internal_note,
                "public_note": public_note,
                "axis_x": axis_x,
                "axis_y": axis_y,
                "data_mode": "live",
                "seed_version": version,
                "fixture_managed": True,
            }
            existing_rp = RoutePoint.objects.filter(route=route, slug=point_slug).first()
            if existing_rp is not None and not existing_rp.fixture_managed and not force_adopt:
                conflicts.append(
                    f"RoutePoint {route.slug}:{point_slug} exists as operator-managed; skipped"
                )
                continue
            if existing_rp is not None and not existing_rp.fixture_managed and force_adopt:
                for key, value in rp_defaults.items():
                    setattr(existing_rp, key, value)
                existing_rp.save()
            else:
                RoutePoint.objects.update_or_create(
                    route=route,
                    slug=point_slug,
                    defaults=rp_defaults,
                )

        if prune:
            RoutePoint.objects.filter(route=route, fixture_managed=True).exclude(slug__in=desired_slugs).delete()
        # Leave operator-managed RoutePoints (fixture_managed=False) even when absent from JSON.
        _restore_manual_route_point_positions(
            route=route,
            fixture_point_slugs=point_slugs,
            manual_positions=manual_positions,
        )
        normalize_and_publish_route(route, rebuild_search=False)

    pruned_routes = 0
    pruned_points = 0
    prune_skipped: list[str] = []
    if prune:
        stale_routes = Route.objects.filter(
            destination=destination,
            fixture_managed=True,
        ).exclude(pk__in=kept_route_ids)
        for route in stale_routes:
            # Operator-managed RoutePoints on a fixture route: keep the route and report.
            if route.points.filter(fixture_managed=False).exists():
                prune_skipped.append(
                    f"Route slug={route.slug} still has operator-managed RoutePoints; not pruned"
                )
                continue
            RoutePoint.objects.filter(route=route, fixture_managed=True).delete()
            route.delete()
            pruned_routes += 1

        keep_point_slugs = set(weather_points)
        stale_points = WeatherPoint.objects.filter(
            destination=destination,
            fixture_managed=True,
            data_mode="live",
        ).exclude(slug__in=keep_point_slugs).exclude(slug__startswith="dest:")
        for point in stale_points:
            referenced = (
                RoutePoint.objects.filter(weather_point=point, fixture_managed=False).exists()
                or Route.objects.filter(fixture_managed=False)
                .filter(Q(origin_weather_point=point) | Q(target_weather_point=point) | Q(points__weather_point=point))
                .exists()
                or Destination.objects.filter(weather_point=point).exists()
            )
            if referenced:
                prune_skipped.append(
                    f"WeatherPoint slug={point.slug} still referenced by operator-managed rows; not pruned"
                )
                continue
            # Also skip if any RoutePoint (even fixture) would ProtectedError — delete links first when safe.
            if RoutePoint.objects.filter(weather_point=point).exists():
                # Remaining links are fixture-managed on routes being kept; skip to avoid crash.
                prune_skipped.append(
                    f"WeatherPoint slug={point.slug} still linked by RoutePoint rows; not pruned"
                )
                continue
            point.delete()
            pruned_points += 1

    conflicts.extend(prune_skipped)
    if raise_on_conflict and conflicts:
        raise CatalogImportConflict(conflicts)

    search = rebuild_search_index()
    return {
        "catalog_version": version,
        "destination": destination.slug,
        "weather_point_count": len(weather_points),
        "route_count": len(kept_route_ids),
        "shared_point_slugs": sorted(weather_points),
        "destination_weather_point": destination_point.slug if destination_point is not None else None,
        "pruned": prune,
        "pruned_routes": pruned_routes,
        "pruned_points": pruned_points,
        "conflicts": conflicts,
        **search,
    }


def bootstrap_live_catalog_if_empty(*, catalog_file: str = DEFAULT_CATALOG_FILE) -> dict | None:
    """Seed the packaged catalog only when no live WeatherPoints exist.

    Safe default for production startup: never sync/prune on every restart.
    """
    from hawatch.modules.catalog.runtime import live_catalog_is_empty

    if not live_catalog_is_empty():
        return None
    return seed_catalog(catalog_file=catalog_file, prune=False)

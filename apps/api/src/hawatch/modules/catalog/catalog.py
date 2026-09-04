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
from django.db.models import Q

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


TIMING_CONFIDENCE_VALUES = {"high", "medium", "low"}
TIMING_STATUS_VALUES = {choice for choice, _label in Route.TimingStatus.choices}


def _restore_manual_route_point_positions(
    *, route: Route, fixture_point_slugs: list[str], manual_positions: list[tuple[int, int]]
) -> None:
    """Reinsert operator-managed RoutePoints at their previous ordinal slots."""
    fixture_points = {
        point.slug: point
        for point in RoutePoint.objects.filter(route=route, slug__in=fixture_point_slugs)
    }
    ordered_fixtures = [fixture_points[slug] for slug in fixture_point_slugs if slug in fixture_points]
    manual_points = {
        point.pk: point
        for point in RoutePoint.objects.filter(route=route, fixture_managed=False)
    }

    if not ordered_fixtures and not manual_points:
        return

    # Put manual rows back into the slots they occupied before the fixture
    # refresh. Do not touch sort orders when the desired order is already
    # present; repeated imports must remain genuinely idempotent.
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

    current = list(route.points.order_by("sort_order", "pk").values_list("pk", "sort_order"))
    desired = [(point.pk, index) for index, point in enumerate(combined, start=1)]
    if current == desired:
        return
    from hawatch.modules.routes.publish import shift_route_point_sort_orders

    shift_route_point_sort_orders(route)
    for index, point in enumerate(combined, start=1):
        RoutePoint.objects.filter(pk=point.pk).update(sort_order=index)


def _validate_route_timing(route_key: str, route: dict, point_slugs: set[str]) -> None:
    """Validate a complete timing block; ambiguous routes remain pending."""
    timing = route.get("timing")
    status = route.get("timing_status", Route.TimingStatus.PENDING)
    if status not in TIMING_STATUS_VALUES:
        raise ValueError(f"Route {route_key} has invalid timing_status: {status}")
    if timing is None:
        if status != Route.TimingStatus.PENDING:
            raise ValueError(f"Route {route_key} has timing_status={status} but no timing block")
        return
    if status == Route.TimingStatus.PENDING:
        raise ValueError(f"Route {route_key} has a timing block but timing_status=pending")

    ordered = list(route.get("points") or [])
    cumulative = timing.get("cumulative_minutes")
    if not isinstance(cumulative, dict) or not cumulative:
        raise ValueError(f"Route {route_key} timing.cumulative_minutes is required when timing is present")
    missing = sorted(set(ordered) - set(cumulative))
    extra = sorted(set(cumulative) - set(ordered))
    if missing:
        raise ValueError(f"Route {route_key} timing missing cumulative entries: {', '.join(missing)}")
    if extra:
        raise ValueError(f"Route {route_key} timing includes points not on the route: {', '.join(extra)}")
    try:
        values = [int(cumulative[slug]) for slug in ordered]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Route {route_key} timing cumulative values must be integers") from exc
    if not values or values[0] != 0:
        raise ValueError(f"Route {route_key} first cumulative_minutes must be 0")
    for previous, current in zip(values, values[1:]):
        if current <= previous:
            raise ValueError(f"Route {route_key} cumulative_minutes must be strictly monotonic")
    one_way = route.get("one_way_minutes")
    if one_way is None:
        raise ValueError(f"Route {route_key} one_way_minutes is required when timing is present")
    if int(one_way) != values[-1]:
        raise ValueError(f"Route {route_key} one_way_minutes ({one_way}) must equal final cumulative ({values[-1]})")
    if route.get("round_trip_minutes") is not None:
        raise ValueError(f"Route {route_key} must not set round_trip_minutes; use one_way_minutes")
    method = str(timing.get("method") or "").strip()
    if not method:
        raise ValueError(f"Route {route_key} timing.method is required for {status}")
    version = str(timing.get("version") or "").strip()
    if not version:
        raise ValueError(f"Route {route_key} timing.version is required for {status}")
    confidence = str(timing.get("confidence") or "").strip()
    if confidence not in TIMING_CONFIDENCE_VALUES:
        raise ValueError(f"Route {route_key} timing.confidence must be one of {sorted(TIMING_CONFIDENCE_VALUES)}")
    uncertainty = timing.get("uncertainty_minutes")
    try:
        if uncertainty is None or int(uncertainty) < 0:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Route {route_key} timing.uncertainty_minutes must be a non-negative integer") from exc
    sources = timing.get("source_urls")
    if not isinstance(sources, list) or not sources or not all(isinstance(url, str) and url.strip() for url in sources):
        raise ValueError(f"Route {route_key} timing.source_urls must be a non-empty list")
    segments = timing.get("segment_minutes")
    if segments is not None:
        if not isinstance(segments, dict) or set(segments) != set(ordered):
            raise ValueError(f"Route {route_key} segment_minutes keys must match route points")
        derived = _derive_segments({slug: int(cumulative[slug]) for slug in ordered}, ordered)
        for slug in ordered:
            if int(segments[slug]) != derived[slug]:
                raise ValueError(f"Route {route_key} segment_minutes[{slug}] must match cumulative difference")


def _validate_document_shape(data: dict) -> None:
    for key in ("catalog_version", "point", "weather_points", "routes"):
        if key not in data:
            raise ValueError(f"Catalog is missing required key: {key}")
    if not isinstance(data["point"], dict):
        raise ValueError("point must be an object")
    if not isinstance(data["routes"], dict):
        raise ValueError("routes must be an object")
    if not isinstance(data["weather_points"], dict) or not data["weather_points"]:
        raise ValueError("weather_points must be a non-empty object")
    points = set(data["weather_points"])
    for slug, row in data["weather_points"].items():
        if not isinstance(row, dict) or not str(row.get("name") or "").strip():
            raise ValueError(f"WeatherPoint {slug}.name is required")
    if _point_slug(data) not in points:
        raise ValueError("primary point does not exist in weather_points")
    shared_rows = data.get("shared_weather_points") or []
    if not isinstance(shared_rows, list) or len(shared_rows) != len(set(shared_rows)):
        raise ValueError("shared_weather_points must be a unique list")
    shared = set(shared_rows)
    overlap = points & shared
    if overlap:
        raise ValueError("shared_weather_points must not repeat local weather points: " + ", ".join(sorted(overlap)))
    points |= shared
    for key, route in data["routes"].items():
        if not isinstance(route, dict):
            raise ValueError(f"Route {key} must be an object")
        ordered = route.get("points") or []
        if not ordered or len(ordered) != len(set(ordered)):
            raise ValueError(f"Route {key} must contain unique ordered points")
        missing = sorted(set(ordered) - points)
        if missing:
            raise ValueError(f"Route {key} references missing points: {', '.join(missing)}")
        public_notes = route.get("public_point_notes") or {}
        if not isinstance(public_notes, dict) or not set(public_notes).issubset(set(ordered)):
            raise ValueError(f"Route {key} public_point_notes references points outside the route")
        _validate_route_timing(key, route, points)
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
def seed_catalog(
    *,
    catalog: dict | None = None,
    catalog_file: str | None = None,
    prune: bool = False,
    force_adopt: bool = False,
    raise_on_conflict: bool = False,
    rebuild_search: bool = True,
) -> dict:
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
            "popular_order": profile.get("popular_order", 0) if slug == _point_slug(data) else 0, "is_popular": bool(profile.get("is_popular", False)) if slug == _point_slug(data) else False, "seo_indexable": bool(profile.get("seo_indexable", True)),
            "climate": row.get("climate") or profile.get("climate", "alpine"), "status": row.get("status") or (WeatherPoint.Status.UNRESOLVED_ELEVATION if row.get("elevation_m") is None else WeatherPoint.Status.APPROVED), "provenance": WeatherPoint.Provenance.CURATED,
            "catalog_version": version, "data_mode": "live", "seed_version": version, "ingest_enabled": True, "fixture_managed": True,
            "is_active": bool(row.get("is_active", profile.get("is_active", True))),
        }
        if existing is None:
            existing = WeatherPoint.objects.create(slug=slug, **defaults)
        else:
            changed_fields = [key for key, value in defaults.items() if getattr(existing, key) != value]
            for key, value in defaults.items():
                setattr(existing, key, value)
            if changed_fields:
                existing.save(update_fields=sorted(set(changed_fields + ["updated_at"])))
        points[slug] = existing
    for slug in data.get("shared_weather_points") or []:
        shared = WeatherPoint.objects.filter(slug=slug, is_active=True).first()
        if shared is None:
            raise ValueError(f"Shared WeatherPoint does not exist: {slug}")
        points[slug] = shared

    kept_routes: list[int] = []
    pruned_routes = 0
    pruned_points = 0
    for catalog_key, row in data["routes"].items():
        ordered = list(row["points"])
        if any(slug not in points for slug in ordered):
            conflicts.append(f"Route {row['slug']} skipped: missing point")
            continue
        timing = _timing(row)
        route, created = Route.objects.get_or_create(
            slug=row["slug"],
            defaults={
                "title": row["title"],
                "subtitle": row["subtitle"],
                "trail_label": row["trail_label"],
                "origin": row["origin"],
                "target_label": row["target_label"],
                "region": row["region"],
                "origin_location": points[ordered[0]].location,
                "fixture_managed": True,
            },
        )
        if not created and not route.fixture_managed and not force_adopt:
            conflicts.append(f"Route slug={route.slug} is operator-managed; skipped")
            kept_routes.append(route.pk)
            continue
        route_values = {
            "title": row["title"], "subtitle": row["subtitle"], "trail_label": row["trail_label"],
            "origin": row["origin"], "target_label": row["target_label"], "region": row["region"],
            "distance_km": row.get("distance_km"), "ascent_m": row.get("ascent_m"), "one_way_minutes": timing["one_way"],
            "default_start_minutes": row.get("default_start_minutes", 360), "timing_status": timing["status"],
            "timing_method": timing["method"], "timing_version": timing["version"], "timing_confidence": timing["confidence"],
            "timing_uncertainty_minutes": timing["uncertainty"], "timing_source_urls": timing["sources"],
            "featured": row.get("featured", False), "sort_order": row.get("sort_order", 0),
            "origin_location": points[ordered[0]].location, "origin_weather_point": points[ordered[0]],
            "target_weather_point": points[ordered[-1]], "catalog_key": catalog_key, "data_mode": "live",
            "seed_version": version, "fixture_managed": True,
        }
        changed_route_fields = [field for field, value in route_values.items() if getattr(route, field) != value]
        for field, value in route_values.items():
            setattr(route, field, value)
        if changed_route_fields:
            route.save(update_fields=sorted(set(changed_route_fields + ["updated_at"])))
        # Preserve operator-managed RoutePoints in the slots where the
        # operator placed them. Fixture rows are rewritten from catalog truth.
        manual_positions = list(
            RoutePoint.objects.filter(route=route, fixture_managed=False)
            .order_by("sort_order", "pk")
            .values_list("pk", "sort_order")
        )
        manual_slug_collisions = set(
            RoutePoint.objects.filter(route=route, fixture_managed=False, slug__in=ordered)
            .values_list("slug", flat=True)
        )
        if manual_slug_collisions and not force_adopt:
            conflicts.append(
                f"Route {route.slug} skipped: operator-managed RoutePoint slug collision "
                f"({', '.join(sorted(manual_slug_collisions))})"
            )
            kept_routes.append(route.pk)
            continue

        from hawatch.modules.routes.publish import shift_route_point_sort_orders

        current_rows = list(route.points.order_by("sort_order", "pk").values_list("slug", "sort_order", flat=False))
        current_slugs = [slug for slug, _sort_order in current_rows]
        if current_slugs != ordered or [sort_order for _slug, sort_order in current_rows] != list(range(1, len(current_rows) + 1)):
            shift_route_point_sort_orders(route)
        for index, slug in enumerate(ordered):
            wp = points[slug]
            rp, _ = RoutePoint.objects.get_or_create(
                route=route,
                slug=slug,
                defaults={
                    "weather_point": wp,
                    "name": wp.name,
                    "sort_order": index + 1,
                    "fixture_managed": True,
                },
            )
            if not rp.fixture_managed and not force_adopt:
                conflicts.append(f"RoutePoint {route.slug}:{slug} is operator-managed; skipped")
                continue
            x, y = axis_for_index(index, len(ordered))
            point_row = data["weather_points"].get(slug) or {}
            values = {
                "weather_point": wp,
                "name": wp.name,
                "elevation_m": wp.elevation_m,
                "location": wp.location,
                "base_minutes": timing["cumulative"].get(slug),
                "segment_minutes": timing["segments"].get(slug),
                "cumulative_minutes": timing["cumulative"].get(slug),
                "progress_pct": round(timing["cumulative"].get(slug, 0) / timing["one_way"] * 100, 2) if timing["one_way"] else None,
                "timing_status": timing["status"] if timing["status"] != Route.TimingStatus.PENDING else RoutePoint.TimingStatus.PENDING,
                "sort_order": index + 1,
                "internal_note": str(point_row.get("evidence_note", "") or "")[:255],
                "public_note": str((row.get("public_point_notes") or {}).get(slug, ""))[:255],
                "axis_x": x,
                "axis_y": y,
                "data_mode": "live",
                "seed_version": version,
                "fixture_managed": True,
            }
            changed_fields = [key for key, value in values.items() if getattr(rp, key) != value]
            for key, value in values.items(): setattr(rp, key, value)
            if changed_fields:
                rp.save(update_fields=sorted(set(changed_fields + ["updated_at"])))
        if prune:
            route.points.filter(fixture_managed=True).exclude(slug__in=ordered).delete()
        _restore_manual_route_point_positions(
            route=route,
            fixture_point_slugs=ordered,
            manual_positions=manual_positions,
        )
        normalize_and_publish_route(route, rebuild_search=False)
        kept_routes.append(route.pk)
    if prune:
        stale_routes = Route.objects.filter(
            fixture_managed=True,
            data_mode="live",
            seed_version=version,
        ).exclude(pk__in=kept_routes)
        for stale_route in stale_routes:
            if stale_route.points.filter(fixture_managed=False).exists():
                conflicts.append(f"Route slug={stale_route.slug} still has operator-managed RoutePoints; not pruned")
                continue
            stale_route.delete()
            pruned_routes += 1

        # There is no Destination owner after point unification. Restrict
        # pruning to rows from this catalog (plus unversioned fixture rows,
        # which are the explicit stale-import case) and never remove a point
        # still referenced by any route/operator record.
        stale_points = WeatherPoint.objects.filter(
            fixture_managed=True,
            data_mode="live",
        ).filter(Q(catalog_version=version) | Q(catalog_version="")).exclude(slug__in=set(points))
        for stale_point in stale_points:
            if RoutePoint.objects.filter(weather_point=stale_point).exists():
                conflicts.append(f"WeatherPoint slug={stale_point.slug} still linked by RoutePoint rows; not pruned")
                continue
            referenced = Route.objects.filter(fixture_managed=False).filter(
                Q(origin_weather_point=stale_point) | Q(target_weather_point=stale_point)
            ).exists()
            if referenced:
                conflicts.append(f"WeatherPoint slug={stale_point.slug} still referenced by operator-managed rows; not pruned")
                continue
            stale_point.delete()
            pruned_points += 1
    if raise_on_conflict and conflicts:
        raise CatalogImportConflict(conflicts)
    search = rebuild_search_index() if rebuild_search else {"entries": 0}
    return {
        "catalog_version": version,
        "point": _point_slug(data),
        "weather_point_count": len(points),
        "route_count": len(kept_routes),
        "shared_point_slugs": sorted(points),
        "pruned": prune,
        "pruned_routes": pruned_routes,
        "pruned_points": pruned_points,
        "conflicts": conflicts,
        **search,
    }


def bootstrap_live_catalog_if_empty(*, catalog_file: str = DEFAULT_CATALOG_FILE) -> dict | None:
    from hawatch.modules.catalog.runtime import live_catalog_is_empty
    return seed_catalog(catalog_file=catalog_file, prune=False) if live_catalog_is_empty() else None

from __future__ import annotations

import hashlib
import json
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django.db import migrations
from django.db.models import Q


ROUTE_SLUG = "damavand-western"
KEEP_POINT_SLUG = "damavand_west_5008"
REMOVED_POINT_SLUGS = {
    "damavand_simorgh",
    "damavand_west_5326",
    "damavand_west_5505",
}


def _checksum_payload(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _remove_point_values_from_url(url: str, removed_indexes: set[int], point_count: int) -> str:
    """Remove matching coordinate/elevation values from an Open-Meteo batch URL."""
    if not url:
        return ""
    parsed = urlsplit(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    for key in ("latitude", "longitude", "elevation"):
        values = query.get(key)
        if not values or len(values) != 1:
            return ""
        parts = values[0].split(",")
        if len(parts) != point_count:
            return ""
        query[key] = [",".join(value for index, value in enumerate(parts) if index not in removed_indexes)]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query, doseq=True), parsed.fragment))


def _scrub_snapshot_batches(raw_response: object) -> tuple[object, int]:
    if not isinstance(raw_response, dict) or not isinstance(raw_response.get("batches"), list):
        return raw_response, 0

    batches = []
    removed_count = 0
    for batch in raw_response["batches"]:
        if not isinstance(batch, dict) or not isinstance(batch.get("point_ids"), list):
            batches.append(batch)
            continue

        point_ids = batch["point_ids"]
        removed_indexes = {
            index for index, point_id in enumerate(point_ids) if point_id in REMOVED_POINT_SLUGS
        }
        if not removed_indexes:
            batches.append(batch)
            continue

        removed_count += len(removed_indexes)
        kept_indexes = [index for index in range(len(point_ids)) if index not in removed_indexes]
        sanitized_batch = dict(batch)
        sanitized_batch["point_ids"] = [point_ids[index] for index in kept_indexes]

        payload = batch.get("payload")
        if isinstance(payload, list) and len(payload) == len(point_ids):
            sanitized_batch["payload"] = [payload[index] for index in kept_indexes]
        else:
            # Do not retain an opaque payload that may contain the removed row.
            sanitized_batch["payload"] = []

        sanitized_batch["url"] = _remove_point_values_from_url(
            str(batch.get("url") or ""), removed_indexes, len(point_ids)
        )
        if sanitized_batch["point_ids"]:
            batches.append(sanitized_batch)

    sanitized_response = dict(raw_response)
    sanitized_response["batches"] = batches
    return sanitized_response, removed_count


def remove_damavand_western_points(apps, schema_editor):
    Route = apps.get_model("routes", "Route")
    RoutePoint = apps.get_model("routes", "RoutePoint")
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    ForecastSnapshot = apps.get_model("forecasts", "ForecastSnapshot")
    SearchIndexEntry = apps.get_model("catalog", "SearchIndexEntry")

    route = Route.objects.filter(slug=ROUTE_SLUG).first()
    if route is None:
        return

    current_slugs = set(route.points.values_list("slug", flat=True))
    missing_points = REMOVED_POINT_SLUGS - current_slugs
    if missing_points:
        raise RuntimeError(
            "Refusing to partially remove Damavand western points; missing route points: "
            + ", ".join(sorted(missing_points))
        )
    if KEEP_POINT_SLUG not in current_slugs:
        raise RuntimeError(
            f"Refusing to remove Damavand western points; required point is missing: {KEEP_POINT_SLUG}"
        )

    removable_points = list(
        RoutePoint.objects.filter(route=route, slug__in=REMOVED_POINT_SLUGS)
        .select_related("weather_point")
    )
    weather_point_ids = [point.weather_point_id for point in removable_points if point.weather_point_id]

    # Remove the route links first because RoutePoint.weather_point is protected.
    RoutePoint.objects.filter(pk__in=[point.pk for point in removable_points]).delete()

    # A deleted point must not be shared by another route, destination, or a
    # canonical route endpoint. Stop the migration if the live data differs
    # from the audited production shape instead of leaving dangling catalog
    # references behind.
    protected_slugs = list(
        WeatherPoint.objects.filter(pk__in=weather_point_ids)
        .filter(
            Q(route_links__isnull=False)
            | Q(destination_profile__isnull=False)
            | Q(origin_routes__isnull=False)
            | Q(target_routes__isnull=False)
        )
        .values_list("slug", flat=True)
        .distinct()
    )
    if protected_slugs:
        raise RuntimeError(
            "Refusing to delete shared Damavand western points: "
            + ", ".join(sorted(protected_slugs))
        )

    SearchIndexEntry.objects.filter(weather_point_slug__in=REMOVED_POINT_SLUGS).delete()
    WeatherPoint.objects.filter(pk__in=weather_point_ids).delete()

    # Keep the route's start, the selected western ridge point, and the summit,
    # then recalculate dense ordering and the segment durations between them.
    kept_points = list(route.points.order_by("sort_order", "pk"))
    for point in kept_points:
        point.sort_order += 1000
        point.save(update_fields=["sort_order"])

    previous_cumulative = None
    for index, point in enumerate(kept_points, start=1):
        fields = ["sort_order"]
        point.sort_order = index
        if point.cumulative_minutes is not None:
            point.segment_minutes = (
                point.cumulative_minutes
                if previous_cumulative is None
                else point.cumulative_minutes - previous_cumulative
            )
            point.base_minutes = point.cumulative_minutes
            fields.extend(["segment_minutes", "base_minutes"])
            previous_cumulative = point.cumulative_minutes
        point.save(update_fields=fields)

    # Forecast rows are cascaded with the WeatherPoint. Remove the same point
    # identifiers, payload rows, and coordinates from retained aggregate raw
    # snapshots, then refresh their integrity checksum.
    for snapshot in ForecastSnapshot.objects.all().only(
        "pk", "point_count", "requested_point_count", "raw_response", "checksum"
    ):
        sanitized_response, removed_count = _scrub_snapshot_batches(snapshot.raw_response)
        if not removed_count:
            continue
        snapshot.raw_response = sanitized_response
        snapshot.point_count = max(0, snapshot.point_count - removed_count)
        snapshot.requested_point_count = max(0, snapshot.requested_point_count - removed_count)
        snapshot.checksum = _checksum_payload(sanitized_response)
        snapshot.save(
            update_fields=["raw_response", "point_count", "requested_point_count", "checksum"]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_search_index"),
        ("routes", "0012_disambiguate_damavand_sulfur_hill"),
    ]

    operations = [
        migrations.RunPython(remove_damavand_western_points, migrations.RunPython.noop),
    ]

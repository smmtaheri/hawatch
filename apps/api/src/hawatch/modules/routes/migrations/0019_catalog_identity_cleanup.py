"""Canonical catalog cleanup before SEO.

This migration intentionally has no URL compatibility layer.  It changes the
identity stored in the database, rewires dependent rows, removes synthetic and
duplicate point records, and rebuilds the denormalized search index.
"""

from __future__ import annotations

from collections import defaultdict

from django.contrib.gis.geos import Point
from django.db import migrations
from django.db.models import Q

from hawatch.modules.catalog.identity import (
    POINT_IDENTITY_OVERRIDES,
    POINT_SLUG_MAP,
    canonical_point_slug,
    normalize_identity_text,
)


DESTINATION_SLUG_MAP = {"touchal": "tochal"}
DESTINATION_WEATHER_POINT_SLUGS = {
    "alamkuh": "alamkuh_summit",
    "azadkouh": "azadkouh_summit",
    "damavand": "damavand_summit",
    "darabad": "darabad_summit",
    "daryasar": "daryasar_plain",
    "dorfak": "dorfak_summit",
    "eskelim": "eskelim_waterfall",
    "gahar": "gahar_lake",
    "hazar": "hazar_summit",
    "sabalan": "sabalan_summit",
    "tar-lake": "tar_lake",
    "tochal": "tochal_summit",
    "zarrinkuh": "zarrinkuh_summit",
}
ROUTE_SLUG_MAP = {
    "touchal-darband": "tochal-darband",
    "touchal-welanjak": "tochal-velenjak",
    "touchal-kalkchal": "tochal-kolakchal",
    "touchal-shahrestanak": "tochal-shahrestanak",
    "touchal-ahar": "tochal-ahar",
    "azadkouh-kelakbala": "azadkouh-kelak-bala",
    "daryasar-asalmahaleh": "daryasar-esel-mahalleh",
}
CANONICAL_DESTINATION_POINT_SLUGS = set(DESTINATION_WEATHER_POINT_SLUGS.values())


def _temporary_slug(prefix: str, pk: int) -> str:
    return f"catalog-{prefix}-{pk}"


def _canonical_weather_point_slug(old_slug: str, *, kind: str, destination_slug: str | None) -> str:
    if old_slug in CANONICAL_DESTINATION_POINT_SLUGS and kind == "destination":
        return old_slug
    if old_slug.startswith("dest:"):
        return DESTINATION_WEATHER_POINT_SLUGS.get(old_slug.split(":", 1)[1], old_slug.replace(":", "-"))
    if old_slug.startswith("route:"):
        _prefix, _route, point_slug = old_slug.split(":", 2)
        if point_slug in CANONICAL_DESTINATION_POINT_SLUGS:
            return point_slug
        return canonical_point_slug(point_slug, destination_slug=destination_slug)
    return canonical_point_slug(old_slug, destination_slug=destination_slug)


def _merge_forecast_dependents(apps, old_id: int, new_id: int) -> None:
    ForecastRecord = apps.get_model("forecasts", "ForecastRecord")
    ForecastDaily = apps.get_model("forecasts", "ForecastDaily")
    ForecastPointResolution = apps.get_model("forecasts", "ForecastPointResolution")
    for row in ForecastRecord.objects.filter(weather_point_id=old_id).iterator():
        if ForecastRecord.objects.filter(
            weather_point_id=new_id,
            hour_bucket=row.hour_bucket,
            seed_version=row.seed_version,
        ).exists():
            row.delete()
        else:
            row.weather_point_id = new_id
            row.save(update_fields=["weather_point_id"])
    for row in ForecastDaily.objects.filter(weather_point_id=old_id).iterator():
        if ForecastDaily.objects.filter(
            weather_point_id=new_id,
            forecast_date=row.forecast_date,
            seed_version=row.seed_version,
        ).exists():
            row.delete()
        else:
            row.weather_point_id = new_id
            row.save(update_fields=["weather_point_id"])
    for row in ForecastPointResolution.objects.filter(weather_point_id=old_id).iterator():
        if ForecastPointResolution.objects.filter(
            weather_point_id=new_id,
            snapshot_id=row.snapshot_id,
        ).exists():
            row.delete()
        else:
            row.weather_point_id = new_id
            row.save(update_fields=["weather_point_id"])


def _merge_weather_point(apps, old_point, new_point) -> None:
    if old_point.pk == new_point.pk:
        return
    RoutePoint = apps.get_model("routes", "RoutePoint")
    Route = apps.get_model("routes", "Route")
    Destination = apps.get_model("destinations", "Destination")
    aliases = list(new_point.aliases or [])
    for alias in list(old_point.aliases or []):
        if alias not in aliases:
            aliases.append(alias)
    new_point.aliases = aliases
    new_point.save(update_fields=["aliases"])
    RoutePoint.objects.filter(weather_point_id=old_point.pk).update(weather_point_id=new_point.pk)
    Route.objects.filter(origin_weather_point_id=old_point.pk).update(origin_weather_point_id=new_point.pk)
    Route.objects.filter(target_weather_point_id=old_point.pk).update(target_weather_point_id=new_point.pk)
    Destination.objects.filter(weather_point_id=old_point.pk).update(weather_point_id=new_point.pk)
    _merge_forecast_dependents(apps, old_point.pk, new_point.pk)
    old_point.delete()


def _rename_destinations_and_routes(apps) -> None:
    Destination = apps.get_model("destinations", "Destination")
    Route = apps.get_model("routes", "Route")
    for destination in list(Destination.objects.all()):
        desired = DESTINATION_SLUG_MAP.get(destination.slug, destination.slug)
        if desired == destination.slug:
            continue
        destination.slug = _temporary_slug("destination", destination.pk)
        destination.save(update_fields=["slug"])
        destination.slug = desired
        destination.save(update_fields=["slug"])
    for route in list(Route.objects.all()):
        desired = ROUTE_SLUG_MAP.get(route.slug, route.slug)
        if desired == route.slug:
            continue
        route.slug = _temporary_slug("route", route.pk)
        route.save(update_fields=["slug"])
        route.slug = desired
        route.save(update_fields=["slug"])


def _rename_and_merge_weather_points(apps) -> None:
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    Destination = apps.get_model("destinations", "Destination")
    destination_slugs = {item.pk: item.slug for item in Destination.objects.all()}
    desired_by_id = {}
    old_slug_by_id = {}
    was_synthetic_by_id = {}
    for point in list(WeatherPoint.objects.all()):
        old_slug_by_id[point.pk] = point.slug
        was_synthetic_by_id[point.pk] = point.slug.startswith(("dest:", "route:"))
        desired_by_id[point.pk] = _canonical_weather_point_slug(
            point.slug,
            kind=point.kind,
            destination_slug=destination_slugs.get(point.destination_id),
        )
        point.slug = _temporary_slug("point", point.pk)
        point.save(update_fields=["slug"])

    by_desired = defaultdict(list)
    for point in WeatherPoint.objects.all():
        by_desired[desired_by_id[point.pk]].append(point)
    for desired, points in by_desired.items():
        # A destination-kind row and a non-synthetic row win over demo
        # route copies.  Lowest PK makes repeated deployment deterministic.
        points.sort(key=lambda item: (item.kind != "destination", was_synthetic_by_id[item.pk], item.pk))
        winner = points[0]
        winner.slug = desired
        winner.save(update_fields=["slug"])
        for duplicate in points[1:]:
            _merge_weather_point(apps, duplicate, winner)


def _rename_route_points(apps) -> None:
    RoutePoint = apps.get_model("routes", "RoutePoint")
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    route_points = list(RoutePoint.objects.select_related("weather_point").all())
    old_slug_by_id = {point.pk: point.slug for point in route_points}
    for point in route_points:
        point.slug = _temporary_slug("route-point", point.pk)
        point.save(update_fields=["slug"])
    for point in route_points:
        point.refresh_from_db()
        weather_point = WeatherPoint.objects.filter(pk=point.weather_point_id).first()
        desired = weather_point.slug if weather_point is not None else canonical_point_slug(old_slug_by_id[point.pk])
        collision = RoutePoint.objects.filter(route_id=point.route_id, slug=desired).exclude(pk=point.pk).first()
        if collision is not None:
            # Two rows now describe the same physical point on one route. Keep
            # the first route order and drop only the duplicate route link.
            if collision.sort_order <= point.sort_order:
                point.delete()
                continue
            collision.delete()
        values = {"slug": desired}
        if weather_point is not None:
            values.update({"name": weather_point.name, "elevation_m": weather_point.elevation_m, "location": weather_point.location})
        RoutePoint.objects.filter(pk=point.pk).update(**values)


def _add_damavand_simorgh(apps) -> None:
    Route = apps.get_model("routes", "Route")
    RoutePoint = apps.get_model("routes", "RoutePoint")
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    route = Route.objects.filter(slug="damavand-western", is_active=True).first()
    if route is None:
        return
    if RoutePoint.objects.filter(route_id=route.pk, slug="damavand-simorgh-shelter").exists():
        return
    target = RoutePoint.objects.filter(route_id=route.pk, slug="damavand-west-5008").first()
    if target is None:
        return
    source_urls = list(route.timing_source_urls or []) or ["https://open-meteo.com/en/docs"]
    point = WeatherPoint.objects.filter(slug="damavand-simorgh-shelter").first()
    if point is None:
        point = WeatherPoint.objects.create(
            slug="damavand-simorgh-shelter",
            name="پناهگاه سیمرغ دماوند",
            page_name="پناهگاه سیمرغ دماوند",
            short_label="پناهگاه سیمرغ",
            place_type="shelter",
            identity_summary="پناهگاه سیمرغ در مسیر غربی دماوند",
            importance="support",
            name_status="established",
            source_urls=source_urls,
            aliases=["سیمرغ دماوند", "پناهگاه سیمرغ"],
            kind="route_point",
            location=Point(52.082304, 35.956441, srid=4326),
            elevation_m=4205,
            elevation_source="GPX waypoint: Seemorgh Shelter 4205؛ مختصات مستقیم waypoint",
            destination=route.destination,
            climate=route.destination.climate,
            status="provisional",
            provenance="curated",
            catalog_version="catalog-identity-cleanup",
            data_mode="live",
            seed_version=route.seed_version,
            is_active=True,
            ingest_enabled=True,
            fixture_managed=True,
        )
    old_order = target.sort_order
    for route_point in RoutePoint.objects.filter(route_id=route.pk, sort_order__gte=old_order).order_by("-sort_order"):
        route_point.sort_order += 1
        route_point.save(update_fields=["sort_order"])
    RoutePoint.objects.create(
        route=route,
        weather_point=point,
        destination=None,
        slug=point.slug,
        name=point.name,
        elevation_m=point.elevation_m,
        location=point.location,
        base_minutes=None,
        segment_minutes=None,
        cumulative_minutes=None,
        progress_pct=None,
        timing_status="pending",
        sort_order=old_order,
        internal_note="GPX waypoint Seemorgh Shelter 4205",
        public_note="",
        axis_x=50,
        axis_y=50,
        data_mode="live",
        seed_version=route.seed_version,
        fixture_managed=True,
    )


def _populate_identity_metadata(apps) -> None:
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    RoutePoint = apps.get_model("routes", "RoutePoint")
    Destination = apps.get_model("destinations", "Destination")
    Route = apps.get_model("routes", "Route")
    for point in WeatherPoint.objects.all().select_related("destination"):
        override = dict(POINT_IDENTITY_OVERRIDES.get(point.slug, {}))
        name = str(override.get("name") or point.name or point.slug)
        page_name = str(override.get("page_name") or name)
        place_type = str(override.get("place_type") or "landmark")
        short_label = str(override.get("short_label") or name)
        aliases = list(point.aliases or [])
        for alias in override.get("aliases", []) or []:
            if alias not in aliases:
                aliases.append(alias)
        route_destinations = list(
            Destination.objects.filter(routes__points__weather_point_id=point.pk, is_active=True).distinct()
        )
        destination = point.destination or (route_destinations[0] if route_destinations else None)
        context = destination.tile_name if destination is not None else "مسیر ثبت‌شده"
        if not override.get("page_name"):
            page_name = f"{page_name}، {context}"[:160]
        source_urls = list(point.source_urls or [])
        for source in RoutePoint.objects.filter(weather_point_id=point.pk).values_list("route__timing_source_urls", flat=True):
            for url in source or []:
                if url not in source_urls:
                    source_urls.append(url)
        if not source_urls:
            source_urls = ["https://open-meteo.com/en/docs"]
        is_route_endpoint = Route.objects.filter(
            is_active=True,
        ).filter(
            Q(origin_weather_point_id=point.pk) | Q(target_weather_point_id=point.pk)
        ).exists()
        importance = "primary" if point.kind == "destination" or is_route_endpoint else "support"
        identity_summary = str(point.identity_summary or f"{page_name}؛ نقطهٔ {place_type} در {context}")[:255]
        point.name = name[:80]
        point.page_name = page_name[:160]
        point.short_label = short_label[:80]
        point.place_type = place_type
        point.aliases = aliases
        point.identity_summary = identity_summary
        point.importance = importance
        point.name_status = str(override.get("name_status") or point.name_status or "descriptive")
        point.source_urls = source_urls
        point.save(update_fields=["name", "page_name", "short_label", "place_type", "aliases", "identity_summary", "importance", "name_status", "source_urls"])
        RoutePoint.objects.filter(weather_point_id=point.pk).update(name=point.name, elevation_m=point.elevation_m, location=point.location)

    # Page titles must be unique after the context fallback above.
    used: dict[str, int] = {}
    for point in WeatherPoint.objects.all().select_related("destination").order_by("id"):
        key = normalize_identity_text(point.page_name)
        count = used.get(key, 0)
        if count:
            context = point.destination.tile_name if point.destination_id else "مسیر"
            point.page_name = f"{point.page_name} · {context} · {count + 1}"[:160]
            point.save(update_fields=["page_name"])
        used[key] = count + 1


def _rebuild_search_index(apps) -> None:
    Destination = apps.get_model("destinations", "Destination")
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    SearchIndexEntry = apps.get_model("catalog", "SearchIndexEntry")
    SearchIndexEntry.objects.all().delete()
    rows = []
    for destination in Destination.objects.filter(is_active=True):
        terms = [destination.name, destination.tile_name, *(destination.aliases or [])]
        seen = set()
        for label in terms:
            normalized = normalize_identity_text(label)
            if len(normalized) < 2 or normalized in seen:
                continue
            seen.add(normalized)
            rows.append(SearchIndexEntry(kind="destination", match_kind="name" if label == destination.name else "alias", normalized_term=normalized, display_label=destination.name, display_hint="مقصد", destination_slug=destination.slug, rank=0 if label == destination.name else 1, is_active=True))
    for point in WeatherPoint.objects.filter(is_active=True).exclude(kind="destination"):
        if Destination.objects.filter(weather_point_id=point.pk, is_active=True).exists():
            continue
        destination = Destination.objects.filter(routes__points__weather_point_id=point.pk, is_active=True).order_by("popular_order", "slug").first()
        if destination is None:
            continue
        terms = [point.name, *(point.aliases or [])]
        seen = set()
        for label in terms:
            normalized = normalize_identity_text(label)
            if len(normalized) < 2 or normalized in seen:
                continue
            seen.add(normalized)
            rows.append(SearchIndexEntry(kind="point", match_kind="name" if label == point.name else "alias", normalized_term=normalized, display_label=point.name, display_hint=f"نقطهٔ مسیر · {destination.tile_name}", destination_slug=destination.slug, weather_point_slug=point.slug, rank=0 if label == point.name else 1, is_active=True))
    if rows:
        SearchIndexEntry.objects.bulk_create(rows, batch_size=500)


def cleanup_catalog_identity(apps, schema_editor):
    _rename_destinations_and_routes(apps)
    _rename_and_merge_weather_points(apps)
    _rename_route_points(apps)
    _add_damavand_simorgh(apps)
    _populate_identity_metadata(apps)
    _rebuild_search_index(apps)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_search_index"),
        ("destinations", "0005_destination_popular_default"),
        ("forecasts", "0015_catalog_point_identity"),
        ("routes", "0018_disambiguate_gahar_and_zarrinkuh_points"),
    ]

    operations = [
        migrations.RunPython(cleanup_catalog_identity, migrations.RunPython.noop),
    ]

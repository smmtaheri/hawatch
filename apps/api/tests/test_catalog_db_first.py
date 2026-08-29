"""Regression: database-first catalog survives bootstrap, import, and ingest selection."""

from __future__ import annotations

from django.contrib.gis.geos import Point
from django.db.models import F
from django.test import override_settings

import pytest

from hawatch.modules.catalog.catalog import bootstrap_live_catalog_if_empty
from hawatch.modules.catalog.runtime import compute_db_catalog_revision, ingestible_weather_points
from hawatch.modules.catalog.search import rebuild_search_index, search_suggestions
from hawatch.modules.catalog.tochal import seed_tochal_catalog
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint
from hawatch.modules.routes.timing import route_timing_complete


@pytest.mark.django_db
def test_manual_weather_point_and_route_survive_bootstrap_and_reimport():
    seed_tochal_catalog()
    destination = Destination.objects.get(slug="touchal")
    manual = WeatherPoint.objects.create(
        slug="manual_ridge_point",
        name="یال دستی",
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.41, 35.87, srid=4326),
        elevation_m=3500,
        elevation_source="Open-Meteo GLO-90 DEM",
        destination=destination,
        status=WeatherPoint.Status.PROVISIONAL,
        provenance=WeatherPoint.Provenance.CURATED,
        catalog_version="",
        data_mode="live",
        is_active=True,
        ingest_enabled=True,
        fixture_managed=False,
    )
    route = Route.objects.create(
        slug="touchal-manual-ridge",
        destination=destination,
        title="یال دستی",
        subtitle="مسیر آزمایشی",
        trail_label="یال دستی",
        origin="شروع",
        destination_label="قله",
        region="تهران",
        distance_km=5.0,
        ascent_m=800,
        one_way_minutes=120,
        timing_status=Route.TimingStatus.ESTIMATED,
        timing_method="manual-admin-v1",
        timing_version="manual-v1",
        timing_confidence="low",
        timing_uncertainty_minutes=30,
        timing_source_urls=["https://example.test/manual"],
        origin_location=manual.location,
        origin_weather_point=manual,
        target_weather_point=WeatherPoint.objects.get(slug="tochal_summit"),
        catalog_key="manual_ridge",
        data_mode="live",
        is_active=True,
        fixture_managed=False,
    )
    for index, (slug, wp, minutes) in enumerate(
        [
            ("manual_ridge_point", manual, 0),
            ("tochal_summit", WeatherPoint.objects.get(slug="tochal_summit"), 120),
        ]
    ):
        RoutePoint.objects.create(
            route=route,
            slug=slug,
            weather_point=wp,
            name=wp.name,
            elevation_m=wp.elevation_m,
            location=wp.location,
            cumulative_minutes=minutes,
            segment_minutes=0 if index == 0 else 120,
            timing_status=Route.TimingStatus.ESTIMATED,
            sort_order=index + 1,
            data_mode="live",
        )

    assert bootstrap_live_catalog_if_empty() is None
    seed_tochal_catalog(prune=False)
    assert WeatherPoint.objects.filter(slug="manual_ridge_point").exists()
    assert Route.objects.filter(slug="touchal-manual-ridge").exists()
    assert WeatherPoint.objects.get(slug="manual_ridge_point").fixture_managed is False


@pytest.mark.django_db
def test_non_pruning_import_preserves_unrelated_rows():
    seed_tochal_catalog()
    destination = Destination.objects.get(slug="touchal")
    WeatherPoint.objects.create(
        slug="orphan_fixture_point",
        name="نقطهٔ یتیم",
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.40, 35.86, srid=4326),
        elevation_m=3000,
        destination=destination,
        data_mode="live",
        fixture_managed=True,
        is_active=True,
        ingest_enabled=True,
    )
    WeatherPoint.objects.create(
        slug="manual_keep_point",
        name="نقطهٔ دستی",
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.402, 35.861, srid=4326),
        elevation_m=3010,
        destination=destination,
        data_mode="live",
        fixture_managed=False,
        is_active=True,
        ingest_enabled=True,
    )
    seed_tochal_catalog(prune=False)
    assert WeatherPoint.objects.filter(slug="orphan_fixture_point").exists()
    assert WeatherPoint.objects.filter(slug="manual_keep_point").exists()


@pytest.mark.django_db
def test_explicit_prune_only_removes_fixture_managed_absent_rows():
    seed_tochal_catalog()
    destination = Destination.objects.get(slug="touchal")
    WeatherPoint.objects.create(
        slug="stale_fixture_point",
        name="نقطهٔ کهنه",
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.40, 35.86, srid=4326),
        elevation_m=3000,
        destination=destination,
        data_mode="live",
        fixture_managed=True,
        is_active=True,
        ingest_enabled=True,
    )
    WeatherPoint.objects.create(
        slug="manual_keep_on_prune",
        name="دستی امن",
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.403, 35.862, srid=4326),
        elevation_m=3020,
        destination=destination,
        data_mode="live",
        fixture_managed=False,
        is_active=True,
        ingest_enabled=True,
    )
    result = seed_tochal_catalog(prune=True)
    assert result["pruned"] is True
    assert not WeatherPoint.objects.filter(slug="stale_fixture_point").exists()
    assert WeatherPoint.objects.filter(slug="manual_keep_on_prune").exists()
    assert WeatherPoint.objects.filter(slug="tochal_summit").exists()


@pytest.mark.django_db
def test_db_added_ingest_enabled_point_is_selected():
    seed_tochal_catalog()
    destination = Destination.objects.get(slug="touchal")
    point = WeatherPoint.objects.create(
        slug="admin_ingest_point",
        name="نقطهٔ ingest",
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.415, 35.875, srid=4326),
        elevation_m=3400,
        destination=destination,
        data_mode="live",
        is_active=True,
        ingest_enabled=True,
        fixture_managed=False,
    )
    Route.objects.create(
        slug="touchal-admin-ingest",
        destination=destination,
        title="ingest",
        subtitle="",
        trail_label="",
        origin="a",
        destination_label="b",
        region="تهران",
        one_way_minutes=60,
        timing_status=Route.TimingStatus.PENDING,
        origin_location=point.location,
        origin_weather_point=point,
        target_weather_point=point,
        data_mode="live",
        is_active=True,
        fixture_managed=False,
    )
    RoutePoint.objects.create(
        route=Route.objects.get(slug="touchal-admin-ingest"),
        slug="admin_ingest_point",
        weather_point=point,
        name=point.name,
        elevation_m=point.elevation_m,
        location=point.location,
        cumulative_minutes=0,
        segment_minutes=0,
        timing_status=Route.TimingStatus.PENDING,
        sort_order=1,
        data_mode="live",
    )

    selected = list(ingestible_weather_points().values_list("slug", flat=True))
    assert "admin_ingest_point" in selected
    assert "tochal_summit" in selected

    inactive = WeatherPoint.objects.get(slug="admin_ingest_point")
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])
    assert "admin_ingest_point" not in list(ingestible_weather_points().values_list("slug", flat=True))

    inactive.is_active = True
    inactive.ingest_enabled = False
    inactive.save(update_fields=["is_active", "ingest_enabled"])
    assert "admin_ingest_point" not in list(ingestible_weather_points().values_list("slug", flat=True))

    slugs = list(ingestible_weather_points(slugs=["tochal_summit"]).values_list("slug", flat=True))
    assert slugs == ["tochal_summit"]
    revision = compute_db_catalog_revision()
    assert revision.startswith("dbrev-")
    assert "tochal_v1" not in revision
    assert "hawatch-tochal-catalog" not in revision


@pytest.mark.django_db
def test_search_index_updates_after_publish():
    seed_tochal_catalog()
    destination = Destination.objects.get(slug="touchal")
    point = WeatherPoint.objects.create(
        slug="searchable_ridge",
        name="یال جستجوپذیر",
        aliases=["یال تست"],
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.41, 35.88, srid=4326),
        elevation_m=3600,
        destination=destination,
        data_mode="live",
        is_active=True,
        ingest_enabled=True,
        fixture_managed=False,
    )
    route = Route.objects.create(
        slug="touchal-searchable",
        destination=destination,
        title="جستجو",
        subtitle="",
        trail_label="",
        origin="a",
        destination_label="b",
        region="تهران",
        timing_status=Route.TimingStatus.PENDING,
        origin_location=point.location,
        origin_weather_point=point,
        target_weather_point=point,
        data_mode="live",
        is_active=True,
        fixture_managed=False,
    )
    RoutePoint.objects.create(
        route=route,
        slug="searchable_ridge",
        weather_point=point,
        name=point.name,
        elevation_m=point.elevation_m,
        location=point.location,
        cumulative_minutes=0,
        timing_status=Route.TimingStatus.PENDING,
        sort_order=1,
        data_mode="live",
        fixture_managed=False,
    )
    rebuild_search_index()
    matches = search_suggestions(query="یال جستجو")
    assert any(item["slug"] == "searchable_ridge" for item in matches)


@pytest.mark.django_db
def test_manual_routepoint_preserved_without_prune():
    seed_tochal_catalog()
    route = Route.objects.get(slug="touchal-darband")
    wp = WeatherPoint.objects.get(slug="tochal_hotel")
    # Make room for an operator-managed point at ordinal slot 2. The next
    # fixture import must retain that placement rather than moving it to the
    # end of the route.
    RoutePoint.objects.filter(route=route).update(sort_order=F("sort_order") + 100)
    RoutePoint.objects.create(
        route=route,
        slug="manual_extra_on_darband",
        weather_point=wp,
        name="نقطهٔ دستی مسیر",
        elevation_m=wp.elevation_m,
        location=wp.location,
        cumulative_minutes=None,
        timing_status=Route.TimingStatus.PENDING,
        sort_order=2,
        data_mode="live",
        fixture_managed=False,
    )
    seed_tochal_catalog(prune=False)
    points = list(route.points.order_by("sort_order"))
    assert [point.slug for point in points][1] == "manual_extra_on_darband"
    assert points[1].fixture_managed is False
    seed_tochal_catalog(prune=True)
    points = list(route.points.order_by("sort_order"))
    assert [point.slug for point in points][1] == "manual_extra_on_darband"


@pytest.mark.django_db
def test_reimport_handles_stale_fixture_point_without_temporary_order_collision():
    """A changed fixture may leave an old fixture point during non-prune import."""
    seed_tochal_catalog()
    route = Route.objects.get(slug="touchal-darband")
    wp = WeatherPoint.objects.get(slug="tochal_hotel")
    # Simulate an older fixture revision whose first point no longer exists in
    # the current catalog. This reproduces the temporary 1001 collision that
    # used to abort an otherwise atomic import.
    RoutePoint.objects.filter(route=route).update(sort_order=F("sort_order") + 100)
    RoutePoint.objects.create(
        route=route,
        slug="retired_fixture_point",
        weather_point=wp,
        name="نقطهٔ قدیمی fixture",
        elevation_m=wp.elevation_m,
        location=wp.location,
        cumulative_minutes=None,
        timing_status=RoutePoint.TimingStatus.PENDING,
        sort_order=1,
        data_mode="live",
        fixture_managed=True,
    )

    seed_tochal_catalog(prune=False)

    points = list(route.points.order_by("sort_order"))
    assert [point.slug for point in points][:6] == [
        "sarband",
        "pas_ghaleh",
        "shirpala",
        "amiri",
        "goleband",
        "tochal_summit",
    ]
    assert points[-1].slug == "retired_fixture_point"


@pytest.mark.django_db
def test_same_slug_collision_skips_operator_managed_rows():
    seed_tochal_catalog()
    summit = WeatherPoint.objects.get(slug="tochal_summit")
    destination = Destination.objects.get(slug="touchal")
    summit.name = "قلهٔ دستی"
    summit.fixture_managed = False
    summit.save(update_fields=["name", "fixture_managed"])
    route = Route.objects.get(slug="touchal-darband")
    replacement = WeatherPoint.objects.get(slug="pas_ghaleh")
    route.target_weather_point = replacement
    route.save(update_fields=["target_weather_point"])
    destination.weather_point = replacement
    destination.save(update_fields=["weather_point"])

    result = seed_tochal_catalog(prune=False)
    assert any("tochal_summit" in item for item in result["conflicts"])
    assert WeatherPoint.objects.get(slug="tochal_summit").name == "قلهٔ دستی"
    route.refresh_from_db()
    destination.refresh_from_db()
    # A skipped fixture point must not be used as a substitute during import.
    assert route.target_weather_point_id == replacement.id
    assert destination.weather_point_id == replacement.id


@pytest.mark.django_db
def test_prune_skips_fixture_point_still_referenced_by_manual_route():
    seed_tochal_catalog()
    destination = Destination.objects.get(slug="touchal")
    stale = WeatherPoint.objects.create(
        slug="stale_referenced_point",
        name="ارجاع دستی",
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.401, 35.861, srid=4326),
        elevation_m=3100,
        destination=destination,
        data_mode="live",
        fixture_managed=True,
        is_active=True,
        ingest_enabled=True,
    )
    Route.objects.create(
        slug="touchal-keeps-stale",
        destination=destination,
        title="نگهبان",
        subtitle="",
        trail_label="",
        origin="a",
        destination_label="b",
        region="تهران",
        timing_status=Route.TimingStatus.PENDING,
        origin_location=stale.location,
        origin_weather_point=stale,
        target_weather_point=stale,
        data_mode="live",
        is_active=True,
        fixture_managed=False,
    )
    result = seed_tochal_catalog(prune=True)
    assert WeatherPoint.objects.filter(slug="stale_referenced_point").exists()
    assert any("stale_referenced_point" in item for item in result["conflicts"])


@pytest.mark.django_db
def test_repeated_imports_idempotent():
    first = seed_tochal_catalog()
    second = seed_tochal_catalog()
    third = seed_tochal_catalog()
    assert first["weather_point_count"] == second["weather_point_count"] == third["weather_point_count"]
    assert Route.objects.filter(destination__slug="touchal", fixture_managed=True).count() == 5


@pytest.mark.django_db
def test_incomplete_timing_remains_pending_and_invariants_hold():
    seed_tochal_catalog()
    for slug in (
        "touchal-darband",
        "touchal-welanjak",
        "touchal-kalkchal",
        "touchal-ahar",
        "touchal-shahrestanak",
    ):
        route = Route.objects.get(slug=slug)
        assert route_timing_complete(
            timing_status=route.timing_status,
            one_way_minutes=route.one_way_minutes,
            points=route.points.all(),
        )

    broken = Route.objects.get(slug="touchal-darband")
    broken.one_way_minutes = 999
    broken.timing_status = Route.TimingStatus.ESTIMATED
    broken.save(update_fields=["one_way_minutes", "timing_status"])
    assert not route_timing_complete(
        timing_status=broken.timing_status,
        one_way_minutes=broken.one_way_minutes,
        points=broken.points.all(),
    )


@pytest.mark.django_db
@override_settings(DEMO_DATA_ENABLED=False)
def test_bootstrap_only_when_empty():
    assert WeatherPoint.objects.filter(data_mode="live").exclude(slug__startswith="dest:").count() == 0
    first = bootstrap_live_catalog_if_empty()
    assert first is not None
    assert WeatherPoint.objects.filter(slug="tochal_summit").exists()
    second = bootstrap_live_catalog_if_empty()
    assert second is None

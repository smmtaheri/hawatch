"""Focused migration/safety tests for Destination.weather_point backfill."""

from __future__ import annotations

import importlib

import pytest
from django.contrib.gis.geos import Point
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone as dj_timezone

from hawatch.modules.catalog.catalog import seed_catalog
from hawatch.modules.catalog.seed import seed_demo_data
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import (
    ForecastDaily,
    ForecastPointResolution,
    ForecastRecord,
    ForecastSnapshot,
    WeatherPoint,
)
from hawatch.modules.routes.models import RoutePoint
from rest_framework.test import APIClient

migration = importlib.import_module(
    "hawatch.modules.destinations.migrations.0004_destination_weather_point"
)
backfill_destination_weather_points = migration.backfill_destination_weather_points


class _Apps:
    @staticmethod
    def get_model(app_label, model_name):
        from django.apps import apps

        return apps.get_model(app_label, model_name)


def _make_destination(**overrides):
    defaults = dict(
        tile_name="دمو",
        name="مقصد دمو",
        short_category="کوه",
        category="کوه",
        category_key="mountain",
        region="تهران",
        elevation_m=2000,
        location=Point(51.4, 35.8, srid=4326),
        image="/images/touchal-banner-clean.png",
        image_alt="دمو",
        popular_order=99,
        climate="alpine",
    )
    defaults.update(overrides)
    return Destination.objects.create(**defaults)


def _make_snapshot():
    now = dj_timezone.now()
    return ForecastSnapshot.objects.create(
        requested_at=now,
        generated_at=now,
        point_count=1,
        requested_point_count=1,
        status="success",
        freshness="ready",
    )


def _make_record(weather_point, *, seed_version: str, temperature_c: float = 5):
    now = dj_timezone.now()
    return ForecastRecord.objects.create(
        weather_point=weather_point,
        forecast_at=now,
        valid_from=now,
        valid_to=now,
        generated_at=now,
        hour_bucket="2026-08-28T10",
        temperature_c=temperature_c,
        apparent_temperature_c=temperature_c - 1,
        weather_code="clear",
        condition_label="صاف",
        icon="☼",
        wind_speed_kmh=4,
        wind_gust_kmh=6,
        wind_direction_deg=180,
        precipitation_probability=0,
        precipitation_mm=0,
        visibility_km=10,
        severity="normal",
        data_mode="demo",
        seed_version=seed_version,
        provider="demo",
    )


def _make_daily(weather_point, *, seed_version: str):
    now = dj_timezone.now()
    return ForecastDaily.objects.create(
        weather_point=weather_point,
        forecast_date=now.date(),
        generated_at=now,
        data_mode="demo",
        seed_version=seed_version,
        provider="demo",
    )


def _make_resolution(weather_point, snapshot):
    return ForecastPointResolution.objects.create(
        snapshot=snapshot,
        weather_point=weather_point,
        requested_latitude=35.8,
        requested_longitude=51.4,
        requested_elevation_m=2000,
        elevation_requested=True,
        resolved_latitude=35.8,
        resolved_longitude=51.4,
        resolved_elevation_m=2000.0,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seeded(db):
    return seed_demo_data(force=True)


@pytest.mark.django_db
def test_destination_profile_points_to_tochal_summit():
    seed_demo_data(force=True)
    touchal = Destination.objects.get(slug="touchal")
    summit = WeatherPoint.objects.get(slug="tochal_summit")
    assert touchal.weather_point_id == summit.id
    assert summit.destination_profile.slug == "touchal"
    assert not WeatherPoint.objects.filter(slug="dest:touchal").exists()


@pytest.mark.django_db
def test_seed_idempotent_never_creates_dest_touchal():
    seed_demo_data(force=True)
    seed_catalog()
    seed_catalog()
    assert WeatherPoint.objects.filter(slug="tochal_summit").count() == 1
    assert not WeatherPoint.objects.filter(slug="dest:touchal").exists()
    assert Destination.objects.get(slug="touchal").weather_point.slug == "tochal_summit"


@pytest.mark.django_db
def test_synthetic_dest_merge_preserves_forecast_dependents(db):
    """Existing dest:{slug} rows merge into canonical without deletion or uniqueness loss."""
    dest = _make_destination(slug="merge-demo", tile_name="ادغام", name="مقصد ادغام", image_alt="ادغام")
    synthetic = WeatherPoint.objects.create(
        slug="dest:merge-demo",
        name="مقصد ادغام",
        kind=WeatherPoint.Kind.DESTINATION,
        location=Point(51.4, 35.8, srid=4326),
        elevation_m=2000,
        destination=dest,
        climate="alpine",
        data_mode="demo",
        seed_version="test-merge-v1",
    )
    snapshot = _make_snapshot()
    _make_record(synthetic, seed_version="test-merge-v1")
    _make_daily(synthetic, seed_version="test-merge-v1")
    _make_resolution(synthetic, snapshot)

    dest.weather_point = None
    dest.save(update_fields=["weather_point"])
    backfill_destination_weather_points(_Apps(), None)

    dest.refresh_from_db()
    assert dest.weather_point_id is not None
    canonical = dest.weather_point
    assert canonical.slug == "merge-demo"
    assert WeatherPoint.objects.filter(slug="dest:merge-demo").exists()
    assert ForecastRecord.objects.filter(weather_point=canonical).count() == 1
    assert ForecastDaily.objects.filter(weather_point=canonical).count() == 1
    assert ForecastPointResolution.objects.filter(weather_point=canonical, snapshot=snapshot).count() == 1
    assert WeatherPoint.objects.filter(pk=synthetic.pk).exists()

    backfill_destination_weather_points(_Apps(), None)
    assert ForecastRecord.objects.filter(weather_point=canonical).count() == 1
    assert ForecastPointResolution.objects.filter(weather_point=canonical).count() == 1
    assert Destination.objects.get(pk=dest.pk).weather_point_id == canonical.id


@pytest.mark.django_db
def test_synthetic_merge_skips_conflicting_forecast_rows(db):
    """Conflicting unique keys stay on synthetic; canonical row is preserved."""
    dest = _make_destination(
        slug="conflict-demo",
        tile_name="تعارض",
        name="مقصد تعارض",
        elevation_m=2100,
        location=Point(51.41, 35.81, srid=4326),
        image_alt="تعارض",
        popular_order=98,
    )
    canonical = WeatherPoint.objects.create(
        slug="conflict-demo",
        name="مقصد تعارض",
        kind=WeatherPoint.Kind.DESTINATION,
        location=Point(51.41, 35.81, srid=4326),
        elevation_m=2100,
        destination=dest,
        climate="alpine",
        data_mode="demo",
        seed_version="test-conflict-v1",
    )
    dest.weather_point = canonical
    dest.save(update_fields=["weather_point"])
    synthetic = WeatherPoint.objects.create(
        slug="dest:conflict-demo",
        name="مقصد تعارض",
        kind=WeatherPoint.Kind.DESTINATION,
        location=Point(51.41, 35.81, srid=4326),
        elevation_m=2100,
        destination=dest,
        climate="alpine",
        data_mode="demo",
        seed_version="test-conflict-v1",
    )
    snapshot = _make_snapshot()
    _make_record(canonical, seed_version="test-conflict-v1", temperature_c=1)
    _make_record(synthetic, seed_version="test-conflict-v1", temperature_c=9)
    _make_daily(canonical, seed_version="test-conflict-v1")
    _make_daily(synthetic, seed_version="test-conflict-v1")
    _make_resolution(canonical, snapshot)
    _make_resolution(synthetic, snapshot)

    backfill_destination_weather_points(_Apps(), None)

    assert ForecastRecord.objects.filter(weather_point=canonical).count() == 1
    assert ForecastRecord.objects.filter(weather_point=synthetic).count() == 1
    assert ForecastRecord.objects.get(weather_point=canonical).temperature_c == 1
    assert ForecastDaily.objects.filter(weather_point=canonical).count() == 1
    assert ForecastDaily.objects.filter(weather_point=synthetic).count() == 1
    assert ForecastPointResolution.objects.filter(weather_point=canonical, snapshot=snapshot).count() == 1
    assert ForecastPointResolution.objects.filter(weather_point=synthetic, snapshot=snapshot).count() == 1
    assert WeatherPoint.objects.filter(pk=synthetic.pk).exists()


@pytest.mark.django_db
def test_ambiguous_slug_collision_leaves_destination_unresolved(db):
    """Do not attach an unrelated route point that merely shares Destination.slug."""
    dest = _make_destination(
        slug="shared-slug",
        tile_name="اشتراک",
        name="مقصد اشتراک",
        popular_order=97,
    )
    unrelated = WeatherPoint.objects.create(
        slug="shared-slug",
        name="نقطهٔ مسیر بی‌ربط",
        kind=WeatherPoint.Kind.ROUTE_POINT,
        location=Point(51.5, 35.9, srid=4326),
        elevation_m=1800,
        destination=None,
        climate="alpine",
        data_mode="demo",
        seed_version="test-collision-v1",
        provenance=WeatherPoint.Provenance.CURATED,
    )
    synthetic = WeatherPoint.objects.create(
        slug="dest:shared-slug",
        name="مقصد اشتراک",
        kind=WeatherPoint.Kind.DESTINATION,
        location=Point(51.4, 35.8, srid=4326),
        elevation_m=2000,
        destination=dest,
        climate="alpine",
        data_mode="demo",
        seed_version="test-collision-v1",
    )
    snapshot = _make_snapshot()
    _make_record(synthetic, seed_version="test-collision-v1", temperature_c=7)
    _make_daily(synthetic, seed_version="test-collision-v1")
    _make_resolution(synthetic, snapshot)
    _make_record(unrelated, seed_version="test-collision-v1", temperature_c=2)

    dest.weather_point = None
    dest.save(update_fields=["weather_point"])
    backfill_destination_weather_points(_Apps(), None)

    dest.refresh_from_db()
    unrelated.refresh_from_db()
    assert dest.weather_point_id is None
    assert unrelated.kind == WeatherPoint.Kind.ROUTE_POINT
    assert ForecastRecord.objects.filter(weather_point=unrelated).count() == 1
    assert ForecastRecord.objects.filter(weather_point=synthetic).count() == 1
    assert ForecastDaily.objects.filter(weather_point=synthetic).count() == 1
    assert ForecastPointResolution.objects.filter(weather_point=synthetic).count() == 1
    assert WeatherPoint.objects.filter(pk=synthetic.pk, slug="dest:shared-slug").exists()


@pytest.mark.django_db(transaction=True)
def test_destination_weather_point_migration_path_skips_slug_collision():
    """Exercise 0004 via MigrationExecutor against historical project state."""
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()

    before = [
        ("destinations", "0003_destination_aliases"),
        ("forecasts", "0011_search_aliases"),
        ("routes", "0004_route_weather_links"),
    ]
    after = [
        ("destinations", "0004_destination_weather_point"),
        ("forecasts", "0011_search_aliases"),
        ("routes", "0004_route_weather_links"),
    ]

    try:
        executor.migrate(before)
        state = executor.loader.project_state(before)
        apps = state.apps

        DestinationHist = apps.get_model("destinations", "Destination")
        WeatherPointHist = apps.get_model("forecasts", "WeatherPoint")
        ForecastRecordHist = apps.get_model("forecasts", "ForecastRecord")
        ForecastDailyHist = apps.get_model("forecasts", "ForecastDaily")
        ForecastSnapshotHist = apps.get_model("forecasts", "ForecastSnapshot")
        ForecastPointResolutionHist = apps.get_model("forecasts", "ForecastPointResolution")

        dest = DestinationHist.objects.create(
            slug="mig-collision",
            tile_name="مهاجرت",
            name="مقصد مهاجرت",
            short_category="کوه",
            category="کوه",
            category_key="mountain",
            region="تهران",
            elevation_m=2200,
            location=Point(51.42, 35.82, srid=4326),
            image="/images/touchal-banner-clean.png",
            image_alt="مهاجرت",
            popular_order=96,
            climate="alpine",
        )
        unrelated = WeatherPointHist.objects.create(
            slug="mig-collision",
            name="نقطهٔ مسیر",
            kind="route_point",
            location=Point(51.43, 35.83, srid=4326),
            elevation_m=1900,
            destination_id=None,
            climate="alpine",
            data_mode="demo",
            seed_version="mig-collision-v1",
            status="approved",
            provenance="curated",
        )
        synthetic = WeatherPointHist.objects.create(
            slug="dest:mig-collision",
            name="مقصد مهاجرت",
            kind="destination",
            location=Point(51.42, 35.82, srid=4326),
            elevation_m=2200,
            destination_id=dest.id,
            climate="alpine",
            data_mode="demo",
            seed_version="mig-collision-v1",
            status="approved",
            provenance="demo_fixture",
        )
        now = dj_timezone.now()
        snapshot = ForecastSnapshotHist.objects.create(
            requested_at=now,
            generated_at=now,
            point_count=1,
            requested_point_count=1,
            status="success",
            freshness="ready",
        )
        ForecastRecordHist.objects.create(
            weather_point_id=synthetic.id,
            forecast_at=now,
            valid_from=now,
            valid_to=now,
            generated_at=now,
            hour_bucket="2026-08-28T10",
            temperature_c=6,
            apparent_temperature_c=5,
            weather_code="clear",
            condition_label="صاف",
            icon="☼",
            wind_speed_kmh=4,
            wind_gust_kmh=6,
            wind_direction_deg=180,
            precipitation_probability=0,
            precipitation_mm=0,
            visibility_km=10,
            severity="normal",
            data_mode="demo",
            seed_version="mig-collision-v1",
            provider="demo",
        )
        ForecastDailyHist.objects.create(
            weather_point_id=synthetic.id,
            forecast_date=now.date(),
            generated_at=now,
            data_mode="demo",
            seed_version="mig-collision-v1",
            provider="demo",
        )
        ForecastPointResolutionHist.objects.create(
            snapshot_id=snapshot.id,
            weather_point_id=synthetic.id,
            requested_latitude=35.82,
            requested_longitude=51.42,
            requested_elevation_m=2200,
            elevation_requested=True,
        )

        executor.migrate(after)
        final_apps = executor.loader.project_state(after).apps
        FinalDestination = final_apps.get_model("destinations", "Destination")
        FinalWeatherPoint = final_apps.get_model("forecasts", "WeatherPoint")
        FinalForecastRecord = final_apps.get_model("forecasts", "ForecastRecord")
        FinalForecastDaily = final_apps.get_model("forecasts", "ForecastDaily")
        FinalForecastPointResolution = final_apps.get_model("forecasts", "ForecastPointResolution")

        final_dest = FinalDestination.objects.get(pk=dest.id)
        assert final_dest.weather_point_id is None
        assert FinalWeatherPoint.objects.filter(pk=unrelated.id, slug="mig-collision").exists()
        assert FinalWeatherPoint.objects.filter(pk=synthetic.id, slug="dest:mig-collision").exists()
        assert FinalForecastRecord.objects.filter(weather_point_id=synthetic.id).count() == 1
        assert FinalForecastRecord.objects.filter(weather_point_id=unrelated.id).count() == 0
        assert FinalForecastDaily.objects.filter(weather_point_id=synthetic.id).count() == 1
        assert FinalForecastPointResolution.objects.filter(weather_point_id=synthetic.id).count() == 1
    finally:
        # Always restore leaf state for the rest of the suite.
        executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db
def test_ensure_catalog_skips_unrelated_destination_slug_collision(db, caplog):
    """Runtime seed must not repurpose a route/shared point that shares a Destination slug."""
    import logging

    from django.conf import settings

    from hawatch.modules.catalog.seed import ensure_catalog

    unrelated = WeatherPoint.objects.create(
        slug="damavand",
        name="نقطهٔ مسیر بی‌ربط",
        kind=WeatherPoint.Kind.ROUTE_POINT,
        location=Point(50.0, 34.0, srid=4326),
        elevation_m=111,
        destination=None,
        climate="alpine",
        data_mode="demo",
        seed_version="seed-collision-v1",
        status=WeatherPoint.Status.APPROVED,
        provenance=WeatherPoint.Provenance.CURATED,
    )
    _make_record(unrelated, seed_version="seed-collision-v1", temperature_c=3)

    with caplog.at_level(logging.ERROR, logger="hawatch.modules.catalog.seed"):
        ensure_catalog(settings.DEMO_SEED_VERSION)

    unrelated.refresh_from_db()
    assert unrelated.kind == WeatherPoint.Kind.ROUTE_POINT
    assert unrelated.elevation_m == 111
    assert float(unrelated.location.x) == 50.0
    assert float(unrelated.location.y) == 34.0
    assert unrelated.destination_id is None
    assert ForecastRecord.objects.filter(weather_point=unrelated).count() == 1

    damavand = Destination.objects.get(slug="damavand")
    assert damavand.weather_point_id is None
    assert damavand.weather_point_id != unrelated.id
    assert any("damavand" in message and "refusing to mutate" in message for message in caplog.messages)


@pytest.mark.django_db
def test_active_route_point_without_legacy_destination_fk(api_client, db):
    seed_demo_data(force=True)
    point = WeatherPoint.objects.get(slug="sarband")
    point.destination = None
    point.save(update_fields=["destination"])
    assert RoutePoint.objects.filter(weather_point=point).exists()
    response = api_client.get("/api/v1/points/sarband/forecast/", {"date": "2026-08-28", "period": "morning"})
    assert response.status_code == 200
    body = response.json()
    assert body["subject"]["slug"] == "sarband"
    assert body["subject"]["canonical_href"] == "/points/sarband"
    assert "forecast" in body
    assert body["forecast"]["meta"]["selected_period"] == "morning"


@pytest.mark.django_db
def test_search_dedupes_destination_profile_weather_point(api_client, seeded):
    results = api_client.get("/api/v1/search/suggestions/", {"q": "توچال"}).json()["results"]
    dests = [item for item in results if item["type"] == "destination" and item["slug"] == "touchal"]
    points = [item for item in results if item["type"] == "point" and item["slug"] == "tochal_summit"]
    assert len(dests) == 1
    assert points == []


@pytest.mark.django_db
def test_route_planner_period_exposes_step_and_hourly_slots(api_client, seeded):
    body = api_client.get(
        "/api/v1/routes/touchal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "06:00"},
    ).json()
    period = body["period"]
    assert period["planner_step_minutes"] == 60
    assert period["planner_start_minutes"] == 360
    assert period["planner_last_start_minutes"] == 660
    assert period["planner_slots"] == [360, 420, 480, 540, 600, 660]
    assert len(period["planner_ticks"]) == 6
    night = api_client.get(
        "/api/v1/routes/touchal-darband/forecast/",
        {"date": "2026-08-28", "period": "night", "start_time": "20:00"},
    ).json()["period"]
    assert night["planner_end_minutes"] == 1440
    assert night["planner_last_start_minutes"] == 1380
    assert night["planner_slots"] == [1080, 1140, 1200, 1260, 1320, 1380]
    assert len(night["planner_ticks"]) == 6

"""Migration backfill, retention, retry, and lock tests."""

from __future__ import annotations

from datetime import timedelta
from io import BytesIO
from urllib.error import HTTPError

import pytest
from django.contrib.gis.geos import Point
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone as dj_timezone

from hawatch.integrations.weather.ingest import (
    IngestLockError,
    cleanup_old_snapshots,
    ingest_lock,
    ingest_weather_points,
    persist_ingest,
)
from hawatch.integrations.weather.providers.open_meteo import OpenMeteoProvider, ProviderPoint
from hawatch.modules.catalog.tochal import seed_tochal_catalog
from hawatch.modules.forecasts.models import ForecastRecord, ForecastSnapshot, WeatherPoint


def _sample_hourly(*, hours: int = 6) -> dict:
    from datetime import datetime

    start = datetime(2026, 8, 27, 0, 0)
    times = [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    return {
        "latitude": 35.85,
        "longitude": 51.43,
        "elevation": 3900.0,
        "hourly": {
            "time": times,
            "temperature_2m": [-5.0] * hours,
            "apparent_temperature": [-6.0] * hours,
            "precipitation_probability": [0] * hours,
            "precipitation": [0.0] * hours,
            "snowfall": [0.0] * hours,
            "weather_code": [0] * hours,
            "visibility": [10000.0] * hours,
            "wind_speed_10m": [10.0] * hours,
            "wind_direction_10m": [180] * hours,
            "wind_gusts_10m": [15.0] * hours,
        },
    }


def _ok_batch(point_ids: list[str], *, hours: int = 6) -> dict:
    return {
        "point_ids": point_ids,
        "status_code": 200,
        "payload": [_sample_hourly(hours=hours) for _ in point_ids],
        "elevation_requested": True,
    }


def _fail_batch(point_ids: list[str], *, status_code: int = 500) -> dict:
    return {
        "point_ids": point_ids,
        "status_code": status_code,
        "payload": {"error": "failed"},
        "elevation_requested": True,
    }


@pytest.mark.django_db(transaction=True)
def test_legacy_route_point_association_backfill():
    """Prove 0005 copies WeatherPoint.route_point → RoutePoint.weather_point before drop."""
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()

    before = [
        ("forecasts", "0004_nullable_cloud_uv"),
        ("routes", "0003_route_weather_links"),
    ]
    after = [("forecasts", "0005_backfill_route_weather_links"), ("routes", "0003_route_weather_links")]

    executor.migrate(before)
    state = executor.loader.project_state(before)
    apps = state.apps

    Destination = apps.get_model("destinations", "Destination")
    Route = apps.get_model("routes", "Route")
    RoutePoint = apps.get_model("routes", "RoutePoint")
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")

    destination = Destination.objects.create(
        slug="mig-dest",
        tile_name="Mig",
        name="Mig",
        short_category="کوه",
        category="کوه",
        category_key="mountain",
        region="تهران",
        elevation_m=3000,
        location=Point(51.4, 35.8, srid=4326),
        image="/x.jpg",
        image_alt="x",
        popular_order=99,
        climate="alpine",
    )
    route = Route.objects.create(
        slug="mig-route",
        destination=destination,
        title="mig",
        subtitle="mig",
        trail_label="mig",
        origin="a",
        destination_label="b",
        region="تهران",
        featured=False,
        sort_order=1,
        origin_location=Point(51.4, 35.8, srid=4326),
    )
    route_point = RoutePoint.objects.create(
        route=route,
        slug="mig-point",
        name="نقطه",
        elevation_m=2500,
        location=Point(51.41, 35.81, srid=4326),
        sort_order=1,
    )
    orphan_point = RoutePoint.objects.create(
        route=route,
        slug="orphan-point",
        name="یتیم",
        elevation_m=2600,
        location=Point(51.42, 35.82, srid=4326),
        sort_order=2,
    )
    weather_point = WeatherPoint.objects.create(
        slug="route:mig-route:mig-point",
        name="نقطه",
        kind="route_point",
        location=Point(51.41, 35.81, srid=4326),
        elevation_m=2500,
        destination=destination,
        route_point_id=route_point.id,
        climate="alpine",
    )
    conflict_point = RoutePoint.objects.create(
        route=route,
        slug="conflict-point",
        name="تداخل",
        elevation_m=2700,
        location=Point(51.43, 35.83, srid=4326),
        sort_order=3,
    )
    other_wp = WeatherPoint.objects.create(
        slug="dest:mig-other",
        name="دیگر",
        kind="destination",
        location=Point(51.43, 35.83, srid=4326),
        elevation_m=2700,
        destination=destination,
        route_point_id=None,
        climate="alpine",
    )
    # Pre-existing different link on the reverse side → must remain unresolved/conflict.
    conflict_point.weather_point_id = other_wp.id
    conflict_point.save(update_fields=["weather_point_id"])
    WeatherPoint.objects.create(
        slug="route:mig-route:conflict-point",
        name="تداخل",
        kind="route_point",
        location=Point(51.43, 35.83, srid=4326),
        elevation_m=2700,
        destination=destination,
        route_point_id=conflict_point.id,
        climate="alpine",
    )
    # Explicit unresolved: orphan_point has no WeatherPoint (no invented association).
    assert orphan_point.weather_point_id is None

    executor.loader.build_graph()
    executor.migrate(after)

    final_state = executor.loader.project_state(after)
    final_apps = final_state.apps
    FinalRoutePoint = final_apps.get_model("routes", "RoutePoint")
    FinalWeatherPoint = final_apps.get_model("forecasts", "WeatherPoint")

    linked = FinalRoutePoint.objects.get(slug="mig-point")
    assert linked.weather_point_id == weather_point.id
    assert FinalRoutePoint.objects.get(slug="orphan-point").weather_point_id is None
    assert FinalRoutePoint.objects.get(slug="conflict-point").weather_point_id == other_wp.id
    field_names = {field.name for field in FinalWeatherPoint._meta.local_fields}
    assert "route_point" not in field_names

    # Return test DB to leaf migrations for subsequent tests in this process.
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db
def test_retention_on_success_partial_and_total_failure():
    seed_tochal_catalog()
    sarband = WeatherPoint.objects.get(slug="sarband")
    shirpala = WeatherPoint.objects.get(slug="shirpala")
    now = dj_timezone.now()

    old_usable = persist_ingest(
        weather_points=[sarband],
        batch_results=[_ok_batch(["sarband"], hours=4)],
    )
    ForecastSnapshot.objects.filter(pk=old_usable.pk).update(generated_at=now - timedelta(days=10))
    old_usable.refresh_from_db()

    old_failed = ForecastSnapshot.objects.create(
        provider="open-meteo",
        source="open-meteo-forecast",
        requested_at=now - timedelta(days=10),
        generated_at=now - timedelta(days=10),
        status=ForecastSnapshot.Status.FAILED,
        freshness=ForecastSnapshot.Freshness.STALE,
        point_count=0,
        raw_response={"old": True},
        checksum="old-failed",
    )

    # Success path creates a new latest usable and must retain it while cleaning older raw rows.
    success = persist_ingest(
        weather_points=[sarband],
        batch_results=[_ok_batch(["sarband"], hours=5)],
    )
    assert success.status == ForecastSnapshot.Status.SUCCESS
    assert not ForecastSnapshot.objects.filter(pk=old_failed.pk).exists()
    assert ForecastSnapshot.objects.filter(pk=success.pk).exists()
    # Previous usable older than 7 days is removable once a newer usable exists.
    assert not ForecastSnapshot.objects.filter(pk=old_usable.pk).exists()

    # Seed another aged failed audit + keep current usable.
    aged_failed = ForecastSnapshot.objects.create(
        provider="open-meteo",
        source="open-meteo-forecast",
        requested_at=now - timedelta(days=9),
        generated_at=now - timedelta(days=9),
        status=ForecastSnapshot.Status.FAILED,
        freshness=ForecastSnapshot.Freshness.STALE,
        point_count=0,
        raw_response={"aged": True},
        checksum="aged-failed",
    )
    usable_before_fail = success.pk
    before_rows = ForecastRecord.objects.filter(weather_point=sarband, data_mode="live").count()

    # Total failure still runs retention and must not delete latest usable / its records.
    returned = persist_ingest(
        weather_points=[sarband, shirpala],
        batch_results=[_fail_batch(["sarband"]), _fail_batch(["shirpala"])],
    )
    assert returned.pk == usable_before_fail
    assert ForecastSnapshot.objects.filter(pk=usable_before_fail).exists()
    assert not ForecastSnapshot.objects.filter(pk=aged_failed.pk).exists()
    assert ForecastRecord.objects.filter(weather_point=sarband, data_mode="live").count() == before_rows
    assert ForecastSnapshot.objects.filter(status=ForecastSnapshot.Status.FAILED).exists()

    # Partial path also enforces retention.
    another_old_failed = ForecastSnapshot.objects.create(
        provider="open-meteo",
        source="open-meteo-forecast",
        requested_at=now - timedelta(days=8),
        generated_at=now - timedelta(days=8),
        status=ForecastSnapshot.Status.FAILED,
        freshness=ForecastSnapshot.Freshness.STALE,
        point_count=0,
        raw_response={},
        checksum="partial-aged-failed",
    )
    persist_ingest(
        weather_points=[sarband, shirpala],
        batch_results=[_ok_batch(["sarband"], hours=3), _fail_batch(["shirpala"])],
    )
    assert not ForecastSnapshot.objects.filter(pk=another_old_failed.pk).exists()
    assert ForecastSnapshot.objects.filter(status=ForecastSnapshot.Status.PARTIAL).exists()


@pytest.mark.django_db
def test_cleanup_never_deletes_latest_usable_even_if_stale_age():
    seed_tochal_catalog()
    summit = WeatherPoint.objects.get(slug="tochal_summit")
    usable = persist_ingest(weather_points=[summit], batch_results=[_ok_batch(["tochal_summit"], hours=3)])
    ForecastSnapshot.objects.filter(pk=usable.pk).update(generated_at=dj_timezone.now() - timedelta(days=30))
    deleted = cleanup_old_snapshots(keep_days=7)
    assert ForecastSnapshot.objects.filter(pk=usable.pk).exists()
    assert deleted == 0 or ForecastSnapshot.objects.filter(pk=usable.pk).exists()


def test_retry_transport_status_zero_and_limits():
    sleeps: list[float] = []
    calls = {"n": 0}

    def bad_opener(_request, timeout=60):
        calls["n"] += 1
        raise TimeoutError("timed out")

    provider = OpenMeteoProvider(max_retries=2, opener=bad_opener, sleeper=sleeps.append)
    result = provider.fetch_batch([ProviderPoint("a", 35.0, 51.0, 100)], include_elevation=True)
    assert result.status_code == 0
    assert "transport_error" in result.payload
    assert result.attempts == 3  # initial + 2 retries
    assert len(sleeps) == 2
    assert sleeps[0] == pytest.approx(0.5)
    assert sleeps[1] == pytest.approx(1.0)


def test_retry_http_429_then_success_and_non_retryable_400():
    sleeps: list[float] = []
    calls = {"n": 0}

    def flaky(_request, timeout=60):
        calls["n"] += 1
        if calls["n"] < 3:

            class R:
                status = 429

                def read(self):
                    return b'{"retry_after": 0.25}'

            return R()

        class Ok:
            status = 200

            def read(self):
                return b"[]"

        return Ok()

    provider = OpenMeteoProvider(max_retries=5, opener=flaky, sleeper=sleeps.append)
    result = provider.fetch_batch([ProviderPoint("a", 35.0, 51.0, 100)], include_elevation=True)
    assert result.status_code == 200
    assert result.attempts == 3
    assert sleeps == [0.25, 0.25]

    sleeps.clear()
    calls["n"] = 0

    def hard_fail(_request, timeout=60):
        calls["n"] += 1

        class R:
            status = 400

            def read(self):
                return b'{"error":"bad"}'

        return R()

    provider = OpenMeteoProvider(max_retries=5, opener=hard_fail, sleeper=sleeps.append)
    result = provider.fetch_batch([ProviderPoint("b", 35.0, 51.0, 100)], include_elevation=True)
    assert result.status_code == 400
    assert result.attempts == 1
    assert sleeps == []


def test_retry_http_error_exception_path():
    sleeps: list[float] = []
    calls = {"n": 0}

    def boom(_request, timeout=60):
        calls["n"] += 1
        raise HTTPError("http://example", 503, "unavailable", hdrs=None, fp=BytesIO(b'{"msg":"x"}'))

    provider = OpenMeteoProvider(max_retries=1, opener=boom, sleeper=sleeps.append)
    result = provider.fetch_batch([ProviderPoint("c", 35.0, 51.0, 100)], include_elevation=True)
    assert result.status_code == 503
    assert result.attempts == 2
    assert len(sleeps) == 1


@pytest.mark.django_db
def test_ingest_lock_covers_fetch_and_persist_and_releases_on_error():
    seed_tochal_catalog()
    points = list(WeatherPoint.objects.filter(slug="tochal_summit"))
    events: list[str] = []

    class TrackingProvider(OpenMeteoProvider):
        def fetch_all(self, provider_points):
            events.append("fetch")
            # Prove lock is held during fetch.
            with pytest.raises(IngestLockError):
                with ingest_lock():
                    pass
            from hawatch.integrations.weather.providers.open_meteo import BatchResult

            return [
                BatchResult(
                    points=list(provider_points),
                    status_code=200,
                    payload=[_sample_hourly(hours=3)],
                    elevation_requested=True,
                    url="https://example.test",
                    attempts=1,
                )
            ]

    snapshot = ingest_weather_points(
        points,
        provider=TrackingProvider(batch_size=10),
        catalog_version="hawatch-tochal-catalog-v1",
        acquire_lock=True,
    )
    assert "fetch" in events
    assert snapshot.status == ForecastSnapshot.Status.SUCCESS
    # Lock released: a new acquire must succeed.
    with ingest_lock():
        events.append("reacquired")
    assert "reacquired" in events

    class ExplodingProvider(OpenMeteoProvider):
        def fetch_all(self, provider_points):
            raise RuntimeError("provider boom")

    with pytest.raises(RuntimeError, match="provider boom"):
        ingest_weather_points(points, provider=ExplodingProvider(), acquire_lock=True)
    # Lock released after exception.
    with ingest_lock():
        pass

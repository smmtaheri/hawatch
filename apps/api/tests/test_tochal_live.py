"""Focused tests for Tochal catalog, Open-Meteo ingest, and API live wiring."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone as dj_timezone
from rest_framework.test import APIClient

from hawatch.integrations.weather.ingest import (
    LIVE_SEED_VERSION,
    ingest_weather_points,
    persist_ingest,
    snapshot_freshness,
    weather_points_to_provider_points,
)
from hawatch.integrations.weather.normalize import map_weather_code, normalize_point_hourly, response_items
from hawatch.integrations.weather.providers.open_meteo import OpenMeteoProvider, ProviderPoint
from hawatch.modules.catalog.seed import seed_demo_data
from hawatch.modules.catalog.tochal import load_tochal_catalog, seed_tochal_catalog
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import ForecastPointResolution, ForecastRecord, ForecastSnapshot, WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint


SHARED_SLUGS = ("tochal_summit", "goleband", "tochal_hotel", "station_7")

EXACT_POINTS = {
    "pas_ghaleh": (35.8361950, 51.4233411, 1936),
    "barfchal": (35.8744485, 51.4373690, 3680),
    "goleband": (35.8809109, 51.4221380, 3860),
    "tochal_summit": (35.8843493, 51.4198766, 3955),
    "ahar": (35.9353996, 51.4635292, 2140),
    "shakarab": (35.9282559, 51.4269378, 2400),
}

TEST_POINT_COORDINATES = {
    "sarband": (35.8280442, 51.4266129),
    "pas_ghaleh": (35.8361950, 51.4233411),
    "shirpala": (35.8550662, 51.4295976),
    "tochal_summit": (35.8843493, 51.4198766),
}


def _sample_hourly(
    *,
    hours: int = 24,
    base_temp: float = -5.0,
    snowfall: float = 0.1,
    latitude: float = 35.85,
    longitude: float = 51.43,
) -> dict:
    start = datetime(2026, 8, 27, 0, 0)
    times = [(start + timedelta(hours=offset)).strftime("%Y-%m-%dT%H:%M") for offset in range(hours)]
    return {
        "latitude": latitude,
        "longitude": longitude,
        "generationtime_ms": 1.2,
        "utc_offset_seconds": 12600,
        "timezone": "Asia/Tehran",
        "timezone_abbreviation": "GMT+3:30",
        "elevation": 3911.0,
        "hourly_units": {"temperature_2m": "°C"},
        "hourly": {
            "time": times,
            "temperature_2m": [base_temp + (i % 5) for i in range(hours)],
            "apparent_temperature": [base_temp - 1 + (i % 5) for i in range(hours)],
            "precipitation_probability": [10] * hours,
            "precipitation": [0.0] * hours,
            "snowfall": [snowfall] * hours,
            "weather_code": [71 if i % 6 == 0 else 2 for i in range(hours)],
            "visibility": [12000.0] * hours,
            "wind_speed_10m": [18.0] * hours,
            "wind_direction_10m": [270] * hours,
            "wind_gusts_10m": [28.0] * hours,
        },
    }


def _batch(point_ids: list[str], *, status_code: int = 200, elevation_requested: bool = True, hours: int = 12):
    if status_code != 200:
        return {
            "point_ids": point_ids,
            "status_code": status_code,
            "payload": {"error": "failed"},
            "elevation_requested": elevation_requested,
        }
    return {
        "point_ids": point_ids,
        "status_code": 200,
        "payload": [
            _sample_hourly(
                hours=hours,
                latitude=TEST_POINT_COORDINATES.get(point_id, (35.85, 51.43))[0],
                longitude=TEST_POINT_COORDINATES.get(point_id, (35.85, 51.43))[1],
            )
            for point_id in point_ids
        ],
        "elevation_requested": elevation_requested,
    }


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_tochal_catalog_exact_values_shared_identity_and_no_duplicates():
    seed_tochal_catalog()
    seed_tochal_catalog()
    catalog = load_tochal_catalog()

    for slug, (lat, lon, elev) in EXACT_POINTS.items():
        point = WeatherPoint.objects.get(slug=slug)
        assert point.location.y == pytest.approx(lat)
        assert point.location.x == pytest.approx(lon)
        assert point.elevation_m == elev

    for slug in ("velenjak", "tochal_hotel", "kolakchal_camp", "ahar", "shakarab", "shahrestanak", "naseri_palace", "naseri_junction"):
        assert WeatherPoint.objects.get(slug=slug).status == WeatherPoint.Status.PROVISIONAL

    goleband = WeatherPoint.objects.get(slug="goleband")
    assert goleband.name == "گوله‌بند"
    assert WeatherPoint.objects.get(slug="lezoon_east").name == "لزون شرقی"
    assert WeatherPoint.objects.get(slug="lezoon_west").name == "لزون غربی"

    expected_points = set(catalog["weather_points"])
    assert WeatherPoint.objects.filter(slug__in=expected_points).count() == len(expected_points)
    assert not WeatherPoint.objects.filter(slug="dopestan").exists()
    assert not WeatherPoint.objects.filter(name__icontains="جمشیدیه").exists()

    for slug in SHARED_SLUGS:
        assert WeatherPoint.objects.filter(slug=slug).count() == 1

    assert RoutePoint.objects.filter(weather_point__slug="tochal_summit").count() == 5
    assert RoutePoint.objects.filter(weather_point__slug="goleband").count() == 2
    assert RoutePoint.objects.filter(weather_point__slug="station_7").count() == 2
    assert RoutePoint.objects.filter(weather_point__slug="tochal_hotel").count() == 2

    for key, row in catalog["routes"].items():
        route = Route.objects.get(slug=row["slug"], catalog_key=key)
        assert list(route.points.order_by("sort_order").values_list("slug", flat=True)) == row["points"]
        assert route.timing_status == Route.TimingStatus.PENDING
        assert route.distance_km is None
        assert route.ascent_m is None

    # No obsolete demo Tochal route points from old fixtures.
    obsolete = {"darband", "amiri-shelter", "loop-pass", "welenjak", "station-7-5", "kolakchal", "dehbahar"}
    assert not RoutePoint.objects.filter(route__destination__slug="touchal", slug__in=obsolete).exists()
    assert Destination.objects.get(slug="touchal").elevation_m == 3955


def test_open_meteo_batching_and_elevation_partition():
    provider = OpenMeteoProvider(batch_size=2)
    points = [
        ProviderPoint("a", 35.1, 51.1, 1000),
        ProviderPoint("b", 35.2, 51.2, 2000),
        ProviderPoint("c", 35.3, 51.3, None),
        ProviderPoint("d", 35.4, 51.4, None),
        ProviderPoint("e", 35.5, 51.5, 3000),
    ]
    with_e, without_e = provider.partition_by_elevation(points)
    assert [p.id for p in with_e] == ["a", "b", "e"]
    assert [p.id for p in without_e] == ["c", "d"]
    assert len(provider.split_batches(with_e)) == 2
    url_with = provider.build_url(with_e[:2], include_elevation=True)
    assert "elevation=" in url_with
    assert "forecast_days=7" in url_with
    url_without = provider.build_url(without_e, include_elevation=False)
    assert "elevation=" not in url_without
    assert "cell_selection=land" in url_without
    url_without_nearest = provider.build_url(without_e, include_elevation=False, cell_selection="nearest")
    assert "cell_selection=nearest" in url_without_nearest
    with pytest.raises(ValueError):
        provider.build_url(without_e, include_elevation=True)


@pytest.mark.django_db
def test_provisional_catalog_elevation_keeps_nearest_provider_cell():
    seed_tochal_catalog()
    hotel, summit = WeatherPoint.objects.filter(slug__in=["tochal_hotel", "tochal_summit"]).order_by("slug")
    points = weather_points_to_provider_points([hotel, summit])
    assert points[0].cell_selection == "nearest"
    assert points[1].cell_selection is None


def test_normalize_does_not_synthesize_cloud_or_uv_and_sets_valid_to():
    raw = _sample_hourly(hours=2, snowfall=1.5)
    rows = normalize_point_hourly(raw, generated_at=dj_timezone.now())
    assert len(rows) == 2
    assert rows[0]["cloud_cover_pct"] is None
    assert rows[0]["uv_index"] is None
    assert "cloud_cover_pct" in rows[0]["fields_unavailable"]
    assert rows[0]["snowfall_cm"] == 1.5
    assert rows[0]["valid_to"] - rows[0]["valid_from"] == timedelta(hours=1)
    assert response_items([raw]) == [raw]
    assert response_items([raw, "malformed", raw]) == []


def test_wind_warning_does_not_replace_sky_condition():
    assert map_weather_code(1, hour=14, wind_kmh=26, gust_kmh=51) == (
        "mainly-clear",
        "عمدتاً صاف",
        "☼",
        "critical",
    )
    assert map_weather_code(61, hour=14, wind_kmh=26, gust_kmh=51) == (
        "rain",
        "باران",
        "☂",
        "critical",
    )
    assert map_weather_code(0, hour=20, wind_kmh=31, gust_kmh=50) == (
        "clear-night",
        "صاف",
        "☾",
        "critical",
    )


def test_bounded_retry_on_429_and_transport():
    sleeps: list[float] = []
    calls = {"n": 0}

    def opener(request, timeout=60):
        calls["n"] += 1
        if calls["n"] < 3:

            class R:
                status = 429

                def read(self):
                    return b'{"retry_after": 0.01}'

            return R()

        class Ok:
            status = 200

            def read(self):
                return b"[]"

        return Ok()

    provider = OpenMeteoProvider(max_retries=3, opener=opener, sleeper=sleeps.append)
    result = provider.fetch_batch([ProviderPoint("a", 35.0, 51.0, 1000)], include_elevation=True)
    assert result.status_code == 200
    assert result.attempts == 3
    assert len(sleeps) == 2
    assert all(delay <= 30 for delay in sleeps)


@pytest.mark.django_db
def test_provider_resolution_preserved_and_not_copied_to_catalog():
    seed_tochal_catalog()
    hotel = WeatherPoint.objects.get(slug="tochal_hotel")
    assert hotel.elevation_m == 3545
    sample = _sample_hourly()
    sample["elevation"] = 3720.5
    sample["latitude"] = 35.8871
    sample["longitude"] = 51.4015
    snapshot = persist_ingest(
        weather_points=[hotel],
        batch_results=[_batch(["tochal_hotel"], elevation_requested=True) | {"payload": [sample]}],
    )
    hotel.refresh_from_db()
    assert hotel.elevation_m == 3545
    resolution = ForecastPointResolution.objects.get(snapshot=snapshot, weather_point=hotel)
    assert resolution.resolved_elevation_m == 3720.5
    assert resolution.elevation_requested is True


@pytest.mark.django_db
def test_partial_ingest_preserves_failed_point_rows():
    seed_tochal_catalog()
    sarband = WeatherPoint.objects.get(slug="sarband")
    shirpala = WeatherPoint.objects.get(slug="shirpala")
    first = persist_ingest(
        weather_points=[sarband, shirpala],
        batch_results=[_batch(["sarband", "shirpala"], hours=6)],
    )
    assert first.status == ForecastSnapshot.Status.SUCCESS
    assert ForecastRecord.objects.filter(weather_point=sarband, data_mode="live").count() == 6
    assert ForecastRecord.objects.filter(weather_point=shirpala, data_mode="live").count() == 6
    old_shirpala_ids = set(
        ForecastRecord.objects.filter(weather_point=shirpala, data_mode="live").values_list("id", flat=True)
    )

    partial = persist_ingest(
        weather_points=[sarband, shirpala],
        batch_results=[
            _batch(["sarband"], hours=8),
            _batch(["shirpala"], status_code=500),
        ],
    )
    assert partial.status == ForecastSnapshot.Status.PARTIAL
    assert ForecastRecord.objects.filter(weather_point=sarband, data_mode="live").count() == 8
    assert set(
        ForecastRecord.objects.filter(weather_point=shirpala, data_mode="live").values_list("id", flat=True)
    ) == old_shirpala_ids


@pytest.mark.django_db
def test_failed_ingest_preserves_previous_usable_snapshot():
    seed_tochal_catalog()
    summit = WeatherPoint.objects.get(slug="tochal_summit")
    good = persist_ingest(weather_points=[summit], batch_results=[_batch(["tochal_summit"], hours=6)])
    assert good.status == ForecastSnapshot.Status.SUCCESS
    before_count = ForecastRecord.objects.filter(weather_point=summit, data_mode="live").count()

    returned = persist_ingest(
        weather_points=[summit],
        batch_results=[_batch(["tochal_summit"], status_code=503)],
    )
    assert returned.pk == good.pk
    assert ForecastSnapshot.objects.filter(status=ForecastSnapshot.Status.FAILED).exists()
    assert ForecastRecord.objects.filter(weather_point=summit, data_mode="live").count() == before_count
    good.refresh_from_db()
    assert good.freshness == ForecastSnapshot.Freshness.STALE


@pytest.mark.django_db
@override_settings(DEMO_DATA_ENABLED=False)
def test_live_mode_never_returns_demo_records(api_client):
    seed_tochal_catalog()
    summit = WeatherPoint.objects.get(slug="tochal_summit")
    # Plant a demo row that must never be served in live mode.
    ForecastRecord.objects.create(
        weather_point=summit,
        forecast_at=dj_timezone.now().replace(minute=0, second=0, microsecond=0),
        valid_from=dj_timezone.now(),
        valid_to=dj_timezone.now() + timedelta(hours=1),
        generated_at=dj_timezone.now(),
        hour_bucket="demo",
        temperature_c=99,
        apparent_temperature_c=99,
        weather_code="clear",
        condition_label="دمو",
        icon="☼",
        wind_speed_kmh=1,
        wind_gust_kmh=2,
        wind_direction_deg=0,
        precipitation_probability=0,
        precipitation_mm=Decimal("0.0"),
        visibility_km=Decimal("10.0"),
        cloud_cover_pct=10,
        uv_index=1,
        severity="normal",
        data_mode="demo",
        source="hawatch-demo",
        seed_version="hawatch-demo-v1",
        provider="demo",
    )
    response = api_client.get("/api/v1/destinations/touchal/forecast/")
    assert response.status_code == 200
    body = response.json()
    assert body["empty"] is True
    assert body["hourly"] == []
    assert body["current"] is None
    assert body["meta"]["data_mode"] == "live"
    assert body["meta"]["freshness"] == "stale"
    assert all(item.get("temperature_c") != 99 for item in body["hourly"])


@pytest.mark.django_db
@override_settings(DEMO_DATA_ENABLED=False)
def test_api_never_calls_provider_and_exposes_snowfall(monkeypatch, api_client):
    seed_tochal_catalog()
    summit = WeatherPoint.objects.get(slug="tochal_summit")
    persist_ingest(
        weather_points=[summit],
        batch_results=[_batch(["tochal_summit"], hours=48)],
    )

    def boom(*_args, **_kwargs):
        raise AssertionError("Open-Meteo must not be called from API handlers")

    monkeypatch.setattr(OpenMeteoProvider, "fetch_all", boom)
    monkeypatch.setattr(OpenMeteoProvider, "fetch_batch", boom)

    response = api_client.get("/api/v1/destinations/touchal/forecast/")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["provider"] == "open-meteo"
    assert body["hourly"]
    assert "snowfall_cm" in body["hourly"][0]
    assert body["hourly"][0]["cloud_cover_pct"] is None
    assert "cloud_cover_pct" in body["hourly"][0]["fields_unavailable"]

    route = api_client.get("/api/v1/routes/touchal-darband/forecast/").json()
    assert route["timing_pending"] is True
    assert route["points"][0]["arrival_minutes"] is None
    assert route["points"][0]["time"] == "—"


@pytest.mark.django_db
def test_api_reads_do_not_write_catalog(api_client):
    seed_demo_data(force=True)
    before_points = WeatherPoint.objects.count()
    before_routes = Route.objects.count()
    before_links = RoutePoint.objects.count()
    updated_at_slugs = list(WeatherPoint.objects.order_by("slug").values_list("slug", "name", "elevation_m"))

    api_client.get("/api/v1/destinations/")
    api_client.get("/api/v1/destinations/touchal/forecast/")
    api_client.get("/api/v1/routes/touchal-darband/forecast/")

    assert WeatherPoint.objects.count() == before_points
    assert Route.objects.count() == before_routes
    assert RoutePoint.objects.count() == before_links
    assert list(WeatherPoint.objects.order_by("slug").values_list("slug", "name", "elevation_m")) == updated_at_slugs


@pytest.mark.django_db
def test_freshness_stale_behavior():
    seed_tochal_catalog()
    summit = WeatherPoint.objects.get(slug="tochal_summit")
    snapshot = persist_ingest(weather_points=[summit], batch_results=[_batch(["tochal_summit"], hours=6)])
    assert snapshot_freshness(snapshot) == "ready"
    snapshot.generated_at = dj_timezone.now() - timedelta(hours=5)
    snapshot.save(update_fields=["generated_at"])
    assert snapshot_freshness(snapshot) == "stale"


@pytest.mark.django_db
def test_ingest_uses_mocked_provider_batches():
    seed_tochal_catalog()
    points = list(WeatherPoint.objects.filter(slug__in=["sarband", "velenjak"]).order_by("slug"))

    class FakeProvider(OpenMeteoProvider):
        def fetch_all(self, provider_points):
            from hawatch.integrations.weather.providers.open_meteo import BatchResult

            results = []
            for point in provider_points:
                sample = _sample_hourly(hours=12, latitude=point.latitude, longitude=point.longitude)
                sample["elevation"] = 2500.0 if point.elevation_m is None else float(point.elevation_m)
                results.append(
                    BatchResult(
                        points=[point],
                        status_code=200,
                        payload=[sample],
                        elevation_requested=point.elevation_m is not None,
                        url="https://example.test",
                        attempts=1,
                    )
                )
            return results

    snapshot = ingest_weather_points(
        points,
        provider=FakeProvider(batch_size=10),
        catalog_version="hawatch-tochal-catalog-v1",
        acquire_lock=False,
    )
    assert snapshot.status == ForecastSnapshot.Status.SUCCESS
    assert snapshot.point_count == 2
    assert ForecastRecord.objects.filter(snapshot=snapshot, seed_version=LIVE_SEED_VERSION).count() == 24
    velenjak = WeatherPoint.objects.get(slug="velenjak")
    assert velenjak.elevation_m == 1755
    assert ForecastPointResolution.objects.get(weather_point=velenjak, snapshot=snapshot).elevation_requested is True

"""A rejected grid/empty point must not starve its healthy batch neighbours."""
from datetime import datetime, timedelta

import pytest
from django.contrib.gis.geos import Point

from hawatch.integrations.weather.ingest import ingest_weather_points, persist_ingest
from hawatch.integrations.weather.providers.open_meteo import BatchResult, OpenMeteoProvider
from hawatch.modules.forecasts.models import ForecastPointResolution, ForecastRecord, ForecastSnapshot, WeatherPoint


def payload(temp=5):
    start = datetime(2026, 10, 8)
    return {
        "latitude": 35.85, "longitude": 51.43, "elevation": 4000,
        "hourly": {
            "time": [(start + timedelta(hours=i)).isoformat(timespec="minutes") for i in range(6)],
            "temperature_2m": [temp] * 6,
            "apparent_temperature": [temp - 1] * 6,
        },
    }


@pytest.fixture
def points():
    return [WeatherPoint.objects.create(
        slug=f"isolation-{i}", name=f"Point {i}", location=Point(51.43, 35.85),
        elevation_m=4000, data_mode="live",
    ) for i in range(2)]


def persist(points, items):
    return persist_ingest(weather_points=points, batch_results=[{
        "point_ids": [p.slug for p in points], "status_code": 200,
        "payload": items, "elevation_requested": True,
    }])


@pytest.mark.django_db
def test_rejected_grid_preserves_old_point_but_updates_healthy_neighbour(points):
    previous = persist(points, [payload(), payload()])
    old = ForecastRecord.objects.filter(weather_point=points[1]).first()
    distant = payload(10)
    distant["latitude"] = 40
    current = persist(points, [payload(12), distant])
    assert current.status == "partial"
    assert current.point_count == 1
    assert current.requested_point_count == 2
    assert ForecastRecord.objects.filter(weather_point=points[0], snapshot=current).count() == 6
    old.refresh_from_db()
    assert old.snapshot_id == previous.pk
    assert old.temperature_c == 5
    assert not ForecastPointResolution.objects.filter(weather_point=points[1], snapshot=current).exists()


@pytest.mark.django_db
def test_empty_hours_do_not_advance_point_timestamp(points):
    persist(points, [payload(), payload()])
    old = ForecastRecord.objects.filter(weather_point=points[1]).first()
    generated_at = old.generated_at
    empty = payload()
    empty["hourly"] = {"time": []}
    current = persist(points, [payload(11), empty])
    assert current.status == "partial" and current.point_count == 1
    old.refresh_from_db()
    assert old.generated_at == generated_at
    assert not ForecastPointResolution.objects.filter(snapshot=current, weather_point=points[1]).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("retry_valid", [True, False])
def test_nearest_retry_is_targeted_and_still_enforces_grid_gate(points, retry_valid):
    class Provider(OpenMeteoProvider):
        def __init__(self):
            super().__init__()
            self.calls = []

        def fetch_all(self, requested, *, models="best_match"):
            self.calls.append(requested)
            distant = payload()
            distant["latitude"] = 40
            items = [payload(7), distant] if len(self.calls) == 1 else [payload(9) if retry_valid else distant]
            return [BatchResult(
                points=list(requested), status_code=200, payload=items,
                elevation_requested=True, url="https://example.invalid",
                cell_selection="land" if len(self.calls) == 1 else "nearest",
                models=models,
            )]

    provider = Provider()
    current = ingest_weather_points(points, provider=provider)
    assert len(provider.calls) == (2 if retry_valid else 3)
    assert [p.id for p in provider.calls[1]] == [points[1].slug]
    assert provider.calls[1][0].cell_selection == "nearest"
    assert provider.calls[1][0].elevation_m == 4000
    assert current.point_count == (2 if retry_valid else 1)
    assert current.status == ("success" if retry_valid else "partial")
    assert ForecastPointResolution.objects.filter(snapshot=current).count() == current.point_count


@pytest.mark.django_db
@pytest.mark.parametrize("failure", ["http", "empty", "grid", "malformed", "null_readings", "mismatch"])
@pytest.mark.parametrize("fallback_valid", [True, False])
def test_generic_ecmwf_fallback_preserves_old_data_on_failure(points, failure, fallback_valid):
    previous = persist(points, [payload(), payload()])

    class Provider(OpenMeteoProvider):
        def __init__(self):
            super().__init__()
            self.calls = []

        def fetch_all(self, requested, *, models="best_match"):
            self.calls.append((list(requested), models))
            if models == "ecmwf_ifs":
                item = payload(9)
                if not fallback_valid:
                    item["latitude"] = 40
                return [BatchResult(list(requested), 200, [item], True, "https://example.invalid", models=models, cell_selection="nearest")]
            bad = payload()
            status = 200
            if failure == "http":
                status = 503
            elif failure == "empty":
                bad["hourly"] = {"time": []}
            elif failure == "grid":
                bad["latitude"] = 40
            elif failure == "malformed":
                bad["hourly"]["time"] = ["not-a-date"]
            elif failure == "null_readings":
                bad["hourly"]["temperature_2m"] = [None] * 6
            items = [] if failure == "mismatch" else [bad]
            # One healthy point and one failing point, including provisional
            # nearest requests: model fallback must not depend on land selection.
            return [
                BatchResult([requested[0]], 200, [payload(7)], True, "https://example.invalid"),
                BatchResult([requested[1]], status, items, True, "https://example.invalid", cell_selection="nearest"),
            ]

    provider = Provider()
    current = ingest_weather_points(points, provider=provider)
    assert len(provider.calls) == 2
    requested, model = provider.calls[1]
    assert model == "ecmwf_ifs"
    assert [point.id for point in requested] == [points[1].slug]
    assert requested[0].elevation_m == 4000 and requested[0].cell_selection == "nearest"
    assert current.models_param == "best_match+ecmwf_ifs"
    assert current.point_count == (2 if fallback_valid else 1)
    row = ForecastRecord.objects.filter(weather_point=points[1]).first()
    assert row.snapshot_id == (current.pk if fallback_valid else previous.pk)
    assert row.temperature_c == (9 if fallback_valid else 5)


@pytest.mark.django_db
def test_healthy_best_match_never_requests_ecmwf(points):
    class Provider(OpenMeteoProvider):
        def fetch_all(self, requested):
            return [BatchResult(list(requested), 200, [payload(), payload()], True, "https://example.invalid")]

    current = ingest_weather_points(points, provider=Provider())
    assert current.status == "success" and current.models_param == "best_match"


def test_fallback_url_keeps_elevation_and_forecast_contract():
    from urllib.parse import parse_qs, urlsplit
    from hawatch.integrations.weather.providers.open_meteo import ProviderPoint

    provider = OpenMeteoProvider()
    point = ProviderPoint("any-point", 35.85, 51.43, 4000)
    query = parse_qs(urlsplit(provider.build_url([point], include_elevation=True, models="ecmwf_ifs", cell_selection="nearest")).query)
    assert query["models"] == ["ecmwf_ifs"]
    assert query["elevation"] == ["4000"]
    assert query["cell_selection"] == ["nearest"]
    assert query["forecast_days"] == [str(provider.forecast_days)]


@pytest.mark.django_db
def test_misaligned_batch_never_reassigns_provider_items(points):
    previous = persist(points, [payload(), payload()])
    assert persist(points, [payload(15)]).pk == previous.pk
    assert ForecastSnapshot.objects.filter(status="failed").exists()
    assert set(ForecastRecord.objects.values_list("temperature_c", flat=True)) == {5}

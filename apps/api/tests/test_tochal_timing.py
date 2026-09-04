"""Focused tests for Tochal v1 estimated route timing and arrival-aware forecasts."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from django.test import override_settings
from django.utils import timezone as dj_timezone
from rest_framework.test import APIClient

from hawatch.common.time import (
    SPEED_TIME_FACTORS,
    arrival_forecast_at,
    paced_duration_minutes,
    round_to_nearest_5,
    timezone,
)
from hawatch.modules.catalog.catalog import _validate_document_shape, load_catalog_file, seed_catalog
from hawatch.modules.catalog.tochal import load_tochal_catalog, seed_tochal_catalog
from hawatch.modules.forecasts.models import ForecastRecord, WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint

EXPECTED_CUMULATIVE = {
    "tochal-darband": {
        "tochal-sarband-square": 0,
        "tochal-pas-ghaleh-village": 20,
        "tochal-shirpala-shelter": 125,
        "tochal-amiri-shelter": 220,
        "tochal-goleband-ridge": 295,
        "tochal": 315,
    },
    "tochal-velenjak": {
        "tochal-velenjak-parking": 0,
        "tochal-telecabin-station-1": 10,
        "tochal-telecabin-station-2": 85,
        "tochal-telecabin-station-5": 195,
        "tochal-telecabin-station-7": 330,
        "tochal": 360,
    },
    "tochal-kolakchal": {
        "tochal-jamshidieh-park": 0,
        "tochal-kolakchal-camp": 135,
        "tochal-espilat-sarlo-pass": 195,
        "tochal-piyazchal-pass": 250,
        "tochal-lezoon-east": 280,
        "tochal-lezoon-west": 305,
        "tochal-barfchal-peak": 330,
        "tochal-chahar-paloon": 355,
        "tochal-goleband-ridge": 375,
        "tochal": 390,
    },
    "tochal-ahar": {
        "tochal-ahar-village": 0,
        "tochal-shakarab-ahaar": 95,
        "tochal-qezqunchal-peak": 315,
        "tochal-homand-tochal": 360,
        "tochal": 380,
    },
    "tochal-shahrestanak": {
        "tochal-shahrestanak-village": 0,
        "shahrestanak-naseri-palace": 65,
        "tochal-shahrestanak-spring": 115,
        "tochal-shahrestanak-sheepfold-spring": 160,
        "tochal-shahrestanak-pass": 285,
        "tochal-hotel": 310,
        "tochal-telecabin-station-7": 335,
        "tochal": 370,
    },
}

EXPECTED_ROUTE_META = {
    "tochal-darband": {
        "distance_km": 10.3,
        "ascent_m": 2150,
        "method": "web-naismith-total+gpx-profile-v2",
        "confidence": "high",
        "uncertainty_minutes": 20,
    },
    "tochal-velenjak": {
        "distance_km": 16.6,
        "ascent_m": 2150,
        "method": "web-naismith-total+gpx-profile-v2",
        "confidence": "medium",
        "uncertainty_minutes": 35,
    },
    "tochal-kolakchal": {
        "distance_km": 12.2,
        "ascent_m": 2210,
        "method": "gpx-geometry+web-naismith-v3",
        "confidence": "medium",
        "uncertainty_minutes": 45,
    },
    "tochal-ahar": {
        "distance_km": 12.5,
        "ascent_m": 1870,
        "method": "web-naismith-total+gpx-profile-v2",
        "confidence": "medium",
        "uncertainty_minutes": 40,
    },
    "tochal-shahrestanak": {
        "distance_km": 16.2,
        "ascent_m": 1710,
        "method": "composite-gpx+dem+web-reports-v1",
        "confidence": "medium",
        "uncertainty_minutes": 50,
    },
}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tochal_seeded(db):
    return seed_tochal_catalog()


def _seed_point_hourly(
    weather_point: WeatherPoint,
    *,
    day,
    hours: list[int],
    temperature_base: float,
    severity: str = "normal",
    seed_version: str = "timing-test-v1",
    data_mode: str = "demo",
    provider: str = "demo",
):
    now = dj_timezone.now()
    tz = timezone()
    for hour in hours:
        at = datetime(day.year, day.month, day.day, hour, 0, tzinfo=tz)
        ForecastRecord.objects.update_or_create(
            weather_point=weather_point,
            forecast_at=at,
            seed_version=seed_version,
            defaults={
                "valid_from": at,
                "valid_to": at + timedelta(hours=2),
                "generated_at": now,
                "hour_bucket": at.strftime("%Y-%m-%dT%H"),
                "temperature_c": int(temperature_base) + (hour % 10),
                "apparent_temperature_c": int(temperature_base),
                "weather_code": "clear",
                "condition_label": f"نقطه-{weather_point.slug}-{hour}",
                "icon": "☼",
                "wind_speed_kmh": 5 + hour,
                "wind_gust_kmh": 8,
                "wind_direction_deg": 180,
                "precipitation_probability": 0,
                "precipitation_mm": 0,
                "visibility_km": 10,
                "severity": severity,
                "data_mode": data_mode,
                "provider": provider,
            },
        )


@pytest.mark.django_db
def test_tochal_medium_cumulative_times_for_all_five_routes(tochal_seeded):
    for slug, expected in EXPECTED_CUMULATIVE.items():
        route = Route.objects.get(slug=slug)
        meta = EXPECTED_ROUTE_META[slug]
        assert route.timing_status == Route.TimingStatus.ESTIMATED
        assert route.one_way_minutes == expected[list(expected)[-1]]
        assert route.round_trip_minutes is None
        assert float(route.distance_km) == meta["distance_km"]
        assert route.ascent_m == meta["ascent_m"]
        assert route.timing_version == "tochal-timing-v3"
        assert route.timing_method == meta["method"]
        assert route.timing_confidence == meta["confidence"]
        assert route.timing_uncertainty_minutes == meta["uncertainty_minutes"]
        got = {
            point.slug: point.cumulative_minutes
            for point in route.points.order_by("sort_order")
        }
        assert got == expected
        previous = None
        for point in route.points.order_by("sort_order"):
            if previous is None:
                assert point.segment_minutes == 0
            else:
                assert point.segment_minutes == point.cumulative_minutes - previous
            previous = point.cumulative_minutes

    shah = Route.objects.get(slug="tochal-shahrestanak")
    assert shah.timing_status == Route.TimingStatus.ESTIMATED
    assert list(shah.points.order_by("sort_order").values_list("slug", flat=True)) == [
        "tochal-shahrestanak-village",
        "shahrestanak-naseri-palace",
        "tochal-shahrestanak-spring",
        "tochal-shahrestanak-sheepfold-spring",
        "tochal-shahrestanak-pass",
        "tochal-hotel",
        "tochal-telecabin-station-7",
        "tochal",
    ]
    # Valley variant points remain available globally but are not on this mandatory chain.
    for slug in ("tochal-naseri-junction", "tochal-bazarek-pass", "tochal-shahneshin-pass"):
        assert WeatherPoint.objects.filter(slug=slug).exists()
        assert slug not in list(shah.points.values_list("slug", flat=True))


@pytest.mark.django_db
def test_tochal_timing_seed_idempotent(tochal_seeded):
    seed_tochal_catalog()
    seed_tochal_catalog()
    assert Route.objects.filter(target_weather_point__slug="tochal", timing_status="estimated").count() == 5
    assert WeatherPoint.objects.filter(slug="tochal").count() == 1
    assert WeatherPoint.objects.filter(slug="tochal-jamshidieh-park").count() == 1
    assert WeatherPoint.objects.filter(slug="tochal-velenjak-parking").count() == 1
    assert WeatherPoint.objects.filter(slug="tochal-velenjak-village").count() == 1
    assert WeatherPoint.objects.filter(slug="tochal-shahrestanak-pass").count() == 1


@pytest.mark.django_db
def test_catalog_evidence_notes_are_internal_not_route_copy(tochal_seeded):
    parking = RoutePoint.objects.get(route__slug="tochal-velenjak", slug="tochal-velenjak-parking")
    assert parking.public_note == ""
    assert parking.internal_note.startswith("Mandatory Velenjak trailhead parking")


@pytest.mark.django_db
def test_jamshidieh_is_kalkchal_origin_and_hotel_not_on_welanjak(tochal_seeded):
    kalkchal = Route.objects.get(slug="tochal-kolakchal")
    assert list(kalkchal.points.order_by("sort_order").values_list("slug", flat=True))[0] == "tochal-jamshidieh-park"
    assert kalkchal.origin == "جمشیدیه"
    assert kalkchal.timing_confidence == "medium"
    park = WeatherPoint.objects.get(slug="tochal-jamshidieh-park")
    assert park.status == WeatherPoint.Status.PROVISIONAL
    assert park.elevation_m == 1826
    assert park.location.y == pytest.approx(35.824629)
    assert park.location.x == pytest.approx(51.465985)
    assert "Open-Meteo GLO-90" in park.elevation_source

    welanjak = Route.objects.get(slug="tochal-velenjak")
    assert list(welanjak.points.order_by("sort_order").values_list("slug", flat=True))[0] == "tochal-velenjak-parking"
    assert welanjak.origin == "پارکینگ ولنجک"
    parking = WeatherPoint.objects.get(slug="tochal-velenjak-parking")
    assert parking.status == WeatherPoint.Status.PROVISIONAL
    assert parking.elevation_m == 1852
    assert "tochal-hotel" not in list(welanjak.points.values_list("slug", flat=True))
    assert WeatherPoint.objects.filter(slug="tochal-hotel").exists()
    assert WeatherPoint.objects.filter(slug="tochal-velenjak-village").exists()
    assert RoutePoint.objects.filter(weather_point__slug="tochal-hotel").count() == 1


def test_pace_factors_and_five_minute_rounding():
    assert SPEED_TIME_FACTORS == {"آرام": 1.25, "متوسط": 1.00, "سریع": 0.80}
    assert paced_duration_minutes(315, "متوسط") == 315
    assert paced_duration_minutes(315, "آرام") == round_to_nearest_5(315 * 1.25)
    assert paced_duration_minutes(315, "سریع") == round_to_nearest_5(315 * 0.80)
    assert paced_duration_minutes(25, "آرام") == 30  # 31.25 → 30
    assert paced_duration_minutes(115, "سریع") == 90  # 92 → 90


@pytest.mark.django_db
def test_routes_are_not_timing_pending_after_seed(api_client, tochal_seeded):
    for slug in EXPECTED_CUMULATIVE:
        body = api_client.get(
            f"/api/v1/routes/{slug}/forecast/",
            {"date": "2026-08-28", "period": "morning", "start_time": "06:00", "speed": "متوسط"},
        ).json()
        assert body["timing_pending"] is False
        assert body["timing_status"] == "estimated"
        assert body["points"][0]["arrival_minutes"] is not None
        assert "timing pending" not in str(body).lower()
        assert body["points"][0]["time"] != "—"


@pytest.mark.django_db
def test_start_and_speed_change_shift_arrival_and_forecast(api_client, tochal_seeded):
    day = datetime(2026, 8, 28).date()
    for slug in ("tochal-shirpala-shelter", "tochal", "tochal-pas-ghaleh-village"):
        _seed_point_hourly(
            WeatherPoint.objects.get(slug=slug),
            day=day,
            hours=[3, 5, 7, 9, 11, 13, 15, 17],
            temperature_base=10 if slug == "tochal-shirpala-shelter" else 0,
        )

    medium = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    fast = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "06:00", "speed": "سریع"},
    ).json()
    later = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "08:00", "speed": "متوسط"},
    ).json()

    shirpala_m = next(item for item in medium["points"] if item["slug"] == "tochal-shirpala-shelter")
    shirpala_f = next(item for item in fast["points"] if item["slug"] == "tochal-shirpala-shelter")
    shirpala_l = next(item for item in later["points"] if item["slug"] == "tochal-shirpala-shelter")
    assert shirpala_m["arrival_minutes"] == 360 + 125
    assert shirpala_f["arrival_minutes"] == 360 + paced_duration_minutes(125, "سریع")
    assert shirpala_f["arrival_minutes"] < shirpala_m["arrival_minutes"]
    assert shirpala_l["arrival_minutes"] == shirpala_m["arrival_minutes"] + 120
    assert shirpala_m["weather_available"] is True
    assert "tochal-shirpala-shelter" in shirpala_m["condition"]
    assert shirpala_l["forecast_at"] != shirpala_m["forecast_at"]


@pytest.mark.django_db
def test_arrival_crosses_midnight(api_client, tochal_seeded):
    day = datetime(2026, 8, 28).date()
    next_day = day + timedelta(days=1)
    summit = WeatherPoint.objects.get(slug="tochal")
    _seed_point_hourly(summit, day=day, hours=[19, 21, 23], temperature_base=-2)
    _seed_point_hourly(summit, day=next_day, hours=[1, 3, 5], temperature_base=-4)

    body = api_client.get(
        "/api/v1/routes/tochal-ahar/forecast/",
        {"date": "2026-08-28", "period": "night", "start_time": "20:00", "speed": "متوسط"},
    ).json()
    finish = body["points"][-1]
    assert finish["slug"] == "tochal"
    assert finish["arrival_minutes"] == 1200 + 380  # 20:00 + 380 → next calendar day
    arrival_at = arrival_forecast_at(day, finish["arrival_minutes"])
    assert arrival_at.date() == next_day
    assert finish["arrival_at"].startswith("2026-08-29")
    assert finish["weather_available"] is True
    assert finish["weather_point_slug"] == "tochal"
    assert finish["forecast_at"].startswith("2026-08-29T02:") or finish["forecast_at"].startswith("2026-08-29T01:") or finish["forecast_at"].startswith("2026-08-29T03:")
    assert finish["temp"] is not None
    assert finish["state"] == "normal"


@pytest.mark.django_db
def test_shahrestanak_timing_estimated_after_seed(api_client, tochal_seeded):
    body = api_client.get(
        "/api/v1/routes/tochal-shahrestanak/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    assert body["timing_pending"] is False
    assert body["timing_status"] == "estimated"
    assert body["points"][0]["arrival_minutes"] == 360
    assert body["points"][-1]["arrival_minutes"] == 360 + 370
    assert body["points"][0]["time"] != "—"
    assert "timing pending" not in str(body).lower()
    assert [point["slug"] for point in body["points"]] == [
        "tochal-shahrestanak-village",
        "shahrestanak-naseri-palace",
        "tochal-shahrestanak-spring",
        "tochal-shahrestanak-sheepfold-spring",
        "tochal-shahrestanak-pass",
        "tochal-hotel",
        "tochal-telecabin-station-7",
        "tochal",
    ]


@pytest.mark.django_db
@override_settings(DEMO_DATA_ENABLED=False)
def test_each_point_uses_own_weather_no_summit_fallback(api_client, tochal_seeded):
    day = datetime(2026, 8, 28).date()
    summit = WeatherPoint.objects.get(slug="tochal")
    shirpala = WeatherPoint.objects.get(slug="tochal-shirpala-shelter")
    _seed_point_hourly(
        summit, day=day, hours=list(range(0, 24, 2)), temperature_base=-10, data_mode="live", provider="open-meteo"
    )
    # Only seed a far-away hour for shirpala so within-tolerance lookup fails.
    _seed_point_hourly(
        shirpala, day=day, hours=[3], temperature_base=20, data_mode="live", provider="open-meteo"
    )

    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "afternoon", "start_time": "12:00", "speed": "متوسط"},
    ).json()
    shirpala_card = next(item for item in body["points"] if item["slug"] == "tochal-shirpala-shelter")
    # Arrival ~12:00+125min ≈ 14:05 → closest within ±90 may miss hour 03 → unavailable
    assert shirpala_card["weather_available"] is False
    assert shirpala_card["temp"] is None
    assert "summit" not in (shirpala_card["condition"] or "").lower()
    summit_card = next(item for item in body["points"] if item["slug"] == "tochal")
    # Summit still may have weather from its own records near arrival.
    assert summit_card["weather_point_slug"] == "tochal"


@pytest.mark.django_db
@override_settings(DEMO_DATA_ENABLED=False)
def test_late_arrival_keeps_matched_forecast_severity(api_client, tochal_seeded):
    day = datetime(2026, 8, 28).date()
    summit = WeatherPoint.objects.get(slug="tochal")
    # Late arrival (~16:15 for medium Darband from 11:00) must not invent change/critical.
    _seed_point_hourly(
        summit,
        day=day,
        hours=[13, 15, 17],
        temperature_base=-1,
        severity="normal",
        data_mode="live",
        provider="open-meteo",
    )
    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "afternoon", "start_time": "11:00", "speed": "متوسط"},
    ).json()
    finish = body["points"][-1]
    assert finish["arrival_minutes"] >= 900
    assert finish["weather_available"] is True
    assert finish["state"] == "normal"
    assert body["decision"]["state"] == "normal"


@pytest.mark.django_db
@override_settings(DEMO_DATA_ENABLED=False)
def test_critical_route_point_does_not_rewrite_target_hourly(api_client, tochal_seeded):
    day = datetime(2026, 8, 28).date()
    summit = WeatherPoint.objects.get(slug="tochal")
    shirpala = WeatherPoint.objects.get(slug="tochal-shirpala-shelter")
    _seed_point_hourly(
        summit, day=day, hours=[12, 14, 16], temperature_base=-2, severity="normal", data_mode="live", provider="open-meteo"
    )
    _seed_point_hourly(
        shirpala, day=day, hours=[12, 14], temperature_base=8, severity="critical", data_mode="live", provider="open-meteo"
    )

    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "afternoon", "start_time": "12:00", "speed": "متوسط"},
    ).json()
    shirpala_card = next(item for item in body["points"] if item["slug"] == "tochal-shirpala-shelter")
    assert shirpala_card["state"] == "critical"
    assert body["decision"]["state"] == "critical"
    assert body["hourly"]
    assert all(item["state"] == "normal" for item in body["hourly"])
    assert all(item["severity"] == "normal" for item in body["hourly"])


@pytest.mark.django_db
def test_closest_forecast_tie_prefers_earlier_forecast_at(tochal_seeded):
    """Equal absolute distance → earlier forecast_at (then lower pk)."""
    from hawatch.api.v1.serializers import _closest_point_forecast

    shirpala = WeatherPoint.objects.get(slug="tochal-shirpala-shelter")
    tz = timezone()
    target = datetime(2026, 8, 28, 8, 0, tzinfo=tz)
    earlier = datetime(2026, 8, 28, 7, 0, tzinfo=tz)
    later = datetime(2026, 8, 28, 9, 0, tzinfo=tz)
    now = dj_timezone.now()
    # Create later first so a pk-only preference would wrongly pick it.
    for at, label, temp in ((later, "later-tie", 2.0), (earlier, "earlier-tie", 1.0)):
        ForecastRecord.objects.create(
            weather_point=shirpala,
            forecast_at=at,
            seed_version=f"tie-{label}",
            valid_from=at,
            valid_to=at + timedelta(hours=2),
            generated_at=now,
            hour_bucket=at.strftime("%Y-%m-%dT%H"),
            temperature_c=int(temp),
            apparent_temperature_c=int(temp),
            weather_code="clear",
            condition_label=label,
            icon="☼",
            wind_speed_kmh=5,
            wind_gust_kmh=6,
            wind_direction_deg=180,
            precipitation_probability=0,
            precipitation_mm=0,
            visibility_km=10,
            severity="normal",
            data_mode="demo",
            provider="demo",
        )
    payload = _closest_point_forecast(shirpala, target, now=now)
    assert payload is not None
    assert payload["condition"] == "earlier-tie"
    assert payload["forecast_at"].startswith("2026-08-28T07:")


@pytest.mark.django_db
def test_incomplete_estimated_timing_behaves_as_pending(api_client, tochal_seeded):
    route = Route.objects.get(slug="tochal-darband")
    route.one_way_minutes = None
    route.save(update_fields=["one_way_minutes"])
    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    assert route.timing_status == Route.TimingStatus.ESTIMATED
    assert body["timing_pending"] is True
    assert all(point["arrival_minutes"] is None for point in body["points"])
    assert all(point["time"] == "—" for point in body["points"])


@pytest.mark.django_db
def test_legacy_base_minutes_without_cumulative_is_unusable(api_client, tochal_seeded):
    route = Route.objects.get(slug="tochal-darband")
    RoutePoint.objects.filter(route=route).update(cumulative_minutes=None, base_minutes=120)
    # Status remains estimated and one_way remains set, but cumulative is missing.
    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    assert body["timing_pending"] is True
    assert all(point["arrival_minutes"] is None for point in body["points"])
    assert "timing pending" not in str(body).lower()


@pytest.mark.django_db
def test_pending_routepoint_makes_route_timing_unusable(api_client, tochal_seeded):
    from hawatch.api.v1.serializers import route_has_usable_timing

    route = Route.objects.get(slug="tochal-darband")
    point = route.points.get(slug="tochal-shirpala-shelter")
    point.timing_status = RoutePoint.TimingStatus.PENDING
    point.save(update_fields=["timing_status"])
    assert point.cumulative_minutes is not None
    assert route_has_usable_timing(route) is False
    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    assert body["timing_pending"] is True


@pytest.mark.django_db
def test_non_monotonic_or_mismatched_cumulative_is_unusable(api_client, tochal_seeded):
    from hawatch.api.v1.serializers import route_has_usable_timing

    route = Route.objects.get(slug="tochal-darband")
    assert route_has_usable_timing(route) is True

    shirpala = route.points.get(slug="tochal-shirpala-shelter")
    shirpala.cumulative_minutes = 10  # less than pas_ghaleh=20
    shirpala.save(update_fields=["cumulative_minutes"])
    assert route_has_usable_timing(route) is False

    # Restore monotonicity but break final == one_way.
    for slug, value in EXPECTED_CUMULATIVE["tochal-darband"].items():
        route.points.filter(slug=slug).update(cumulative_minutes=value)
    summit = route.points.get(slug="tochal")
    summit.cumulative_minutes = route.one_way_minutes - 5
    summit.save(update_fields=["cumulative_minutes"])
    assert route_has_usable_timing(route) is False
    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    assert body["timing_pending"] is True


@pytest.mark.django_db
def test_complete_estimated_route_remains_usable(api_client, tochal_seeded):
    from hawatch.api.v1.serializers import route_has_usable_timing

    route = Route.objects.get(slug="tochal-darband")
    assert route_has_usable_timing(route) is True
    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    assert body["timing_pending"] is False
    assert body["points"][0]["arrival_minutes"] == body["start_minutes"]
    assert body["points"][-1]["arrival_minutes"] == body["start_minutes"] + 315


def test_catalog_timing_validation_rejects_non_monotonic():
    data = load_catalog_file()
    route = data["routes"]["darband_to_tochal"]
    route["timing"]["cumulative_minutes"]["tochal-shirpala-shelter"] = 10
    with pytest.raises(ValueError, match="strictly monotonic"):
        _validate_document_shape(data)


def test_catalog_timing_validation_rejects_round_trip_field():
    data = load_catalog_file()
    data["routes"]["darband_to_tochal"]["round_trip_minutes"] = 600
    with pytest.raises(ValueError, match="one_way_minutes"):
        _validate_document_shape(data)


def test_catalog_timing_validation_requires_provenance_metadata():
    data = load_catalog_file()
    timing = data["routes"]["darband_to_tochal"]["timing"]
    timing["method"] = ""
    with pytest.raises(ValueError, match="timing.method"):
        _validate_document_shape(data)

    data = load_catalog_file()
    data["routes"]["darband_to_tochal"]["timing"]["confidence"] = ""
    with pytest.raises(ValueError, match="timing.confidence"):
        _validate_document_shape(data)

    data = load_catalog_file()
    data["routes"]["darband_to_tochal"]["timing"]["uncertainty_minutes"] = -1
    with pytest.raises(ValueError, match="uncertainty_minutes"):
        _validate_document_shape(data)

    data = load_catalog_file()
    data["routes"]["darband_to_tochal"]["timing"]["source_urls"] = []
    with pytest.raises(ValueError, match="source_urls"):
        _validate_document_shape(data)


@pytest.mark.django_db
def test_ambiguous_timing_stays_pending(db):
    data = load_tochal_catalog()
    route = data["routes"]["darband_to_tochal"]
    route.pop("timing")
    route["timing_status"] = "pending"
    route.pop("one_way_minutes", None)
    route.pop("distance_km", None)
    route.pop("ascent_m", None)
    # Keep other routes valid.
    seed_catalog(catalog=data)
    assert Route.objects.get(slug="tochal-darband").timing_status == Route.TimingStatus.PENDING
    assert Route.objects.get(slug="tochal-velenjak").timing_status == Route.TimingStatus.ESTIMATED

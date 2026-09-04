"""Focused tests for adaptive forecast periods and route point detail."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as utc_timezone
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from hawatch.common.time import (
    StartTimeValidationError,
    current_period_start_minutes,
    datetime_flags,
    default_forecast_selection,
    format_start_time_wire,
    normalize_start_minutes,
    parse_period,
    parse_start_minutes,
    parse_start_time_value,
    period_last_start_minute,
    period_window,
    resolve_planner_start_minutes,
    timezone,
)
from hawatch.modules.catalog.seed import seed_demo_data
from hawatch.modules.routes.models import Route, RoutePoint


REFERENCE_DATE = datetime.now(tz=timezone()).date()


def tehran_datetime(*, day_offset=0, hour=0, minute=0):
    day = REFERENCE_DATE + timedelta(days=day_offset)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone())


def utc_datetime(*, day_offset=0, hour=0, minute=0):
    day = REFERENCE_DATE + timedelta(days=day_offset)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=utc_timezone.utc)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seeded(db, monkeypatch):
    # Keep the generated forecast window deterministic. The API itself uses
    # the real Tehran clock; only this test fixture freezes the clock so the
    # calendar dates below do not expire as the suite is run on later days.
    fixed_now = tehran_datetime(hour=7, minute=30)
    from hawatch.common.time import now_tehran as real_now_tehran

    def fixed_clock(at=None):
        # Keep the conversion form of now_tehran(at) intact. Serializers use
        # that form for forecast timestamps while views use now_tehran().
        return fixed_now if at is None else real_now_tehran(at)

    monkeypatch.setattr("hawatch.modules.catalog.seed.now_tehran", fixed_clock)
    monkeypatch.setattr("hawatch.api.v1.views.now_tehran", fixed_clock)
    monkeypatch.setattr("hawatch.api.v1.serializers.now_tehran", fixed_clock)
    return seed_demo_data(force=True)


@pytest.mark.django_db
def test_parse_period_accepts_four_periods_and_legacy_noon_alias():
    assert parse_period("midnight") == "midnight"
    assert parse_period("morning") == "morning"
    assert parse_period("noon") == "noon"
    assert parse_period("afternoon") == "noon"
    assert parse_period("night") == "night"
    assert parse_period(None) == "morning"


@pytest.mark.django_db
def test_default_selection_boundaries():
    tz = timezone()
    cases = [
        (tehran_datetime(hour=0, minute=0), REFERENCE_DATE.isoformat(), "midnight"),
        (tehran_datetime(hour=5, minute=59), REFERENCE_DATE.isoformat(), "midnight"),
        (tehran_datetime(hour=6), REFERENCE_DATE.isoformat(), "morning"),
        (tehran_datetime(hour=11, minute=59), REFERENCE_DATE.isoformat(), "morning"),
        (tehran_datetime(hour=12), REFERENCE_DATE.isoformat(), "noon"),
        (tehran_datetime(hour=17, minute=59), REFERENCE_DATE.isoformat(), "noon"),
        (tehran_datetime(hour=18), REFERENCE_DATE.isoformat(), "night"),
        (tehran_datetime(hour=23, minute=59), REFERENCE_DATE.isoformat(), "night"),
    ]
    for at, expected_date, expected_period in cases:
        selected_date, period = default_forecast_selection(at)
        assert selected_date.isoformat() == expected_date
        assert period == expected_period


@pytest.mark.django_db
def test_period_windows_do_not_overlap():
    day = REFERENCE_DATE
    windows = {name: period_window(day, name) for name in ("midnight", "morning", "noon", "night")}
    midnight_end = windows["midnight"][1]
    morning_start = windows["morning"][0]
    morning_end = windows["morning"][1]
    noon_start = windows["noon"][0]
    noon_end = windows["noon"][1]
    night_start = windows["night"][0]
    assert midnight_end == morning_start
    assert morning_end == noon_start
    assert noon_end == night_start
    assert windows["midnight"] == (
        tehran_datetime(hour=0),
        tehran_datetime(hour=6),
    )
    assert windows["morning"] == (
        tehran_datetime(hour=6),
        tehran_datetime(hour=12),
    )
    assert windows["noon"] == (
        tehran_datetime(hour=12),
        tehran_datetime(hour=18),
    )
    assert windows["night"] == (
        tehran_datetime(hour=18),
        tehran_datetime(day_offset=1, hour=0),
    )


@pytest.mark.django_db
def test_point_forecast_four_periods_start_at_midnight(api_client, seeded):
    day = REFERENCE_DATE
    midnight = api_client.get("/api/v1/points/tochal/forecast/", {"date": day.isoformat(), "period": "midnight"}).json()
    morning = api_client.get("/api/v1/points/tochal/forecast/", {"date": day.isoformat(), "period": "morning"}).json()
    noon = api_client.get("/api/v1/points/tochal/forecast/", {"date": day.isoformat(), "period": "noon"}).json()
    night = api_client.get("/api/v1/points/tochal/forecast/", {"date": day.isoformat(), "period": "night"}).json()

    assert [item["hour"] for item in midnight["hourly"]] == [0, 2, 4]
    assert [item["hour"] for item in morning["hourly"]] == [6, 8, 10]
    assert [item["hour"] for item in noon["hourly"]] == [12, 14, 16]
    assert [item["hour"] for item in night["hourly"]] == [18, 20, 22]

    midnight_times = {item["forecast_at"] for item in midnight["hourly"]}
    night_times = {item["forecast_at"] for item in night["hourly"]}
    morning_times = {item["forecast_at"] for item in morning["hourly"]}
    noon_times = {item["forecast_at"] for item in noon["hourly"]}
    assert midnight_times.isdisjoint(morning_times)
    assert night_times.isdisjoint(morning_times)
    assert morning_times.isdisjoint(noon_times)
    assert noon_times.isdisjoint(night_times)

    assert all(item["forecast_at"].startswith(REFERENCE_DATE.isoformat()) for item in midnight["hourly"] + night["hourly"])
    assert morning["meta"]["forecast_validity"]["valid_from"].endswith("+03:30")


@pytest.mark.django_db
def test_explicit_query_params_override_defaults(api_client, seeded):
    outside_window = REFERENCE_DATE - timedelta(days=8)
    response = api_client.get(
        "/api/v1/points/tochal/forecast/",
        {"date": outside_window.isoformat(), "period": "noon"},
    )
    body = response.json()
    assert body["meta"]["selected_date"] == outside_window.isoformat()
    assert body["meta"]["selected_period"] == "noon"


@pytest.mark.django_db
@patch("hawatch.api.v1.views.default_forecast_selection", return_value=(REFERENCE_DATE, "morning"))
def test_defaults_applied_without_query_params(mock_default, api_client, seeded):
    body = api_client.get("/api/v1/points/tochal/forecast/").json()
    assert body["meta"]["selected_date"] == REFERENCE_DATE.isoformat()
    assert body["meta"]["selected_period"] == "morning"
    mock_default.assert_called_once()


@pytest.mark.django_db
def test_period_start_minutes_stay_inside_same_day_windows():
    assert parse_start_minutes("00:30", "midnight", None) == 0
    assert parse_start_minutes("05:30", "midnight", None) == 300
    assert parse_start_minutes("06:00", "morning", None) == 360
    assert parse_start_minutes("11:30", "morning", None) == 660
    assert parse_start_minutes("17:30", "noon", None) == 1020
    assert parse_start_minutes("23:30", "night", None) == 1380


@pytest.mark.django_db
def test_point_midnight_current_at_0130(api_client, seeded):
    tz = timezone()
    at = tehran_datetime(hour=1, minute=30)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get("/api/v1/points/tochal/forecast/").json()
    assert body["meta"]["selected_date"] == REFERENCE_DATE.isoformat()
    assert body["meta"]["selected_period"] == "midnight"
    assert body["current"] is not None
    assert body["current"]["is_current"] is True
    assert "الان" in body["hero"]["status"]
    today = next(day for day in body["days"] if day["date"] == REFERENCE_DATE.isoformat())
    assert today["is_today"] is True


@pytest.mark.django_db
def test_point_default_uses_current_tehran_hour(api_client, seeded):
    tz = timezone()
    at = tehran_datetime(hour=7, minute=30)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get("/api/v1/points/tochal/forecast/").json()

    assert body["meta"]["selected_period"] == "morning"
    assert [item["hour"] for item in body["hourly"]] == [6, 8, 10]
    assert body["current"]["hour"] == 6
    assert body["current"]["is_current"] is True
    assert all(item["is_past"] for item in body["hourly"] if item["hour"] < 6)
    assert body["current"]["hour"] == 6


@pytest.mark.django_db
def test_hourly_cards_mark_the_current_display_window(api_client, seeded):
    tz = timezone()
    at = tehran_datetime(hour=10, minute=30)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get(
            "/api/v1/points/tochal/forecast/",
            {"date": REFERENCE_DATE.isoformat(), "period": "morning"},
        ).json()

    by_hour = {item["hour"]: item for item in body["hourly"]}
    assert by_hour[10]["is_current"] is True
    assert all(by_hour[hour]["is_past"] is True for hour in (6, 8))
    assert sum(item["is_current"] for item in body["hourly"]) == 1


@override_settings(TIME_ZONE="UTC")
def test_forecast_clock_stays_on_official_iran_time():
    assert timezone().key == "Asia/Tehran"
    selected_date, period = default_forecast_selection(utc_datetime(hour=5))
    assert selected_date == REFERENCE_DATE
    assert period == "morning"

    flags = datetime_flags(
        utc_datetime(hour=4, minute=30),
        utc_datetime(hour=5),
    )
    assert flags["is_current"] is True


@pytest.mark.django_db
def test_current_period_start_minutes_floors_without_crossing_exclusive_end():
    tz = timezone()
    cases = [
        (tehran_datetime(hour=5, minute=29), "midnight", 300),
        (tehran_datetime(hour=5, minute=45), "midnight", 300),
        (tehran_datetime(hour=11, minute=45), "morning", 660),
        (tehran_datetime(hour=17, minute=45), "noon", 1020),
        (tehran_datetime(hour=6), "morning", 360),
        (tehran_datetime(hour=12), "noon", 720),
        (tehran_datetime(hour=18), "night", 1080),
    ]
    for at, period, expected in cases:
        assert current_period_start_minutes(period, at) == expected


@pytest.mark.django_db
def test_parse_start_minutes_respects_exclusive_period_end():
    assert parse_start_minutes("06:00", "midnight", None) == 300
    assert parse_start_minutes("12:00", "morning", None) == 660
    assert parse_start_minutes("18:00", "noon", None) == 1020
    assert parse_start_minutes("00:00", "night", None) == 1080


@pytest.mark.django_db
def test_route_point_forecast_endpoint_is_removed(api_client, seeded):
    response = api_client.get(
        "/api/v1/routes/tochal-darband/points/tochal-shirpala-shelter/forecast/",
        {"date": REFERENCE_DATE.isoformat(), "period": "morning"},
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_timing_pending_does_not_invent_arrivals(api_client, seeded):
    # Force pending so the contract stays testable after Tochal v1 estimates ship.
    Route.objects.filter(slug="tochal-darband").update(timing_status=Route.TimingStatus.PENDING)
    RoutePoint.objects.filter(route__slug="tochal-darband").update(
        timing_status=RoutePoint.TimingStatus.PENDING,
        cumulative_minutes=None,
        segment_minutes=None,
    )
    today = REFERENCE_DATE
    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": today.isoformat(), "period": "morning", "start_time": "06:00", "speed": "سریع"},
    ).json()
    assert body["timing_pending"] is True
    assert all(point["arrival_minutes"] is None for point in body["points"])
    assert all(point["time"] == "—" for point in body["points"])
    assert "timing pending" not in body["decision"]["title"].lower()
    assert "حوالی —" not in body["hero"]["status"]
    assert "ETA" not in " ".join(body["decision"]["recommendations"])
    for point in body["points"]:
        assert "weather_available" in point


@pytest.mark.django_db
def test_timing_pending_point_weather_is_unavailable(api_client, seeded):
    Route.objects.filter(slug="tochal-darband").update(timing_status=Route.TimingStatus.PENDING)
    RoutePoint.objects.filter(route__slug="tochal-darband").update(
        timing_status=RoutePoint.TimingStatus.PENDING,
        cumulative_minutes=None,
        segment_minutes=None,
    )
    tz = timezone()
    at = tehran_datetime(hour=10, minute=30)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get(
            "/api/v1/routes/tochal-darband/forecast/",
            {"date": REFERENCE_DATE.isoformat(), "period": "night"},
        ).json()
    assert body["timing_pending"] is True
    for point in body["points"]:
        assert point["weather_available"] is False
        assert point["weather"] is None
        assert point["arrival_minutes"] is None
        assert "زمان‌بندی" in point["condition"]
        assert "timing pending" not in point["condition"].lower()


@pytest.mark.django_db
def test_tochal_canonical_href(api_client, seeded):
    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": REFERENCE_DATE.isoformat(), "period": "morning"},
    ).json()
    summit = next(item for item in body["points"] if item["slug"] == "tochal")
    assert summit["href"] == "/points/tochal"


@pytest.mark.django_db
def test_route_default_start_uses_current_tehran_in_current_period(api_client, seeded):
    tz = timezone()
    at = tehran_datetime(hour=7, minute=30)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get(
            "/api/v1/routes/tochal-darband/forecast/",
            {"date": REFERENCE_DATE.isoformat(), "period": "morning"},
        ).json()
    assert body["start_minutes"] == 420


@pytest.mark.django_db
def test_point_night_period_uses_in_window_reading_at_1030(api_client, seeded):
    tz = timezone()
    at = tehran_datetime(hour=10, minute=30)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get(
            "/api/v1/points/tochal/forecast/",
            {"date": REFERENCE_DATE.isoformat(), "period": "night"},
        ).json()
    allowed_hours = {18, 20, 22}
    assert body["current"] is not None
    assert body["current"]["hour"] in allowed_hours
    assert body["current"]["is_current"] is False
    assert "الان" not in body["hero"]["status"]
    assert all(item["hour"] in allowed_hours for item in body["hourly"])


@pytest.mark.django_db
def test_point_night_period_uses_in_window_reading_at_1030(api_client, seeded):
    tz = timezone()
    at = tehran_datetime(hour=10, minute=30)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get(
            "/api/v1/points/tochal-shirpala-shelter/forecast/",
            {"date": REFERENCE_DATE.isoformat(), "period": "night"},
        ).json()
    allowed_hours = {18, 20, 22}
    assert body["current"] is not None
    assert body["weather"]["hour"] in allowed_hours
    assert body["weather"]["is_current"] is False
    assert "الان" not in body["hero"]["status"]


@pytest.mark.django_db
def test_point_midnight_current_at_0130(api_client, seeded):
    tz = timezone()
    at = tehran_datetime(hour=1, minute=30)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get("/api/v1/points/tochal-shirpala-shelter/forecast/").json()
    assert body["meta"]["selected_date"] == REFERENCE_DATE.isoformat()
    assert body["meta"]["selected_period"] == "midnight"
    assert body["current"]["is_current"] is True
    assert body["current"]["hour"] == 0
    assert "الان" in body["hero"]["status"]


@pytest.mark.django_db
def test_route_period_switch_uses_period_default_not_route_default(api_client, seeded):
    tz = timezone()
    at = tehran_datetime(hour=10, minute=30)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        noon = api_client.get(
            "/api/v1/routes/tochal-darband/forecast/",
            {"date": REFERENCE_DATE.isoformat(), "period": "noon"},
        ).json()
        night = api_client.get(
            "/api/v1/routes/tochal-darband/forecast/",
            {"date": REFERENCE_DATE.isoformat(), "period": "night"},
        ).json()
    assert noon["start_minutes"] == 840
    assert night["start_minutes"] == 1200


@pytest.mark.django_db
def test_route_start_time_floors_off_step_minutes(api_client, seeded):
    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": REFERENCE_DATE.isoformat(), "period": "morning", "start_time": "10:15"},
    ).json()
    assert body["start_minutes"] == 600


@pytest.mark.django_db
def test_normalize_start_minutes_floors_persian_digits():
    assert normalize_start_minutes("۱۰:۱۵", "morning") == 600
    assert resolve_planner_start_minutes(
        REFERENCE_DATE,
        "noon",
        local=tehran_datetime(hour=10, minute=30),
        raw_start="14:15",
    ) == 840


@pytest.mark.django_db
def test_parse_start_time_value_rejects_malformed():
    with pytest.raises(StartTimeValidationError):
        parse_start_time_value("12:xx")
    with pytest.raises(StartTimeValidationError):
        parse_start_time_value("12:00:00")
    with pytest.raises(StartTimeValidationError):
        parse_start_time_value("25:00")
    with pytest.raises(StartTimeValidationError):
        parse_start_time_value("12:60")


@pytest.mark.django_db
def test_legacy_numeric_start_time_minutes():
    assert normalize_start_minutes("360", "morning") == 360
    assert normalize_start_minutes("90", "midnight") == 60


@pytest.mark.django_db
def test_route_invalid_start_time_returns_400(api_client, seeded):
    response = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": REFERENCE_DATE.isoformat(), "period": "morning", "start_time": "12:xx"},
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_start_time_wire_format_is_ascii():
    assert format_start_time_wire(360) == "06:00"
    assert format_start_time_wire(720) == "12:00"


@pytest.mark.django_db
def test_primary_point_links_to_its_own_canonical_page(seeded):
    from hawatch.modules.forecasts.models import WeatherPoint

    summit = WeatherPoint.objects.get(slug="tochal")
    assert summit.kind == WeatherPoint.Kind.PRIMARY
    assert summit.seo_indexable is True


@pytest.mark.django_db
def test_catalog_seed_does_not_create_synthetic_point_slugs(seeded):
    from hawatch.modules.catalog.catalog import seed_catalog
    from hawatch.modules.forecasts.models import WeatherPoint

    seed_catalog()
    seed_catalog()
    assert not WeatherPoint.objects.filter(slug="dest:tochal").exists()
    assert WeatherPoint.objects.filter(slug="tochal").exists()
    assert WeatherPoint.objects.filter(slug="damavand", kind=WeatherPoint.Kind.PRIMARY).exists()
    assert not WeatherPoint.objects.filter(slug="dest:damavand").exists()


@pytest.mark.django_db
def test_shared_weather_point_has_one_canonical_page(api_client, seeded):
    summit = api_client.get("/api/v1/points/tochal/forecast/", {"date": REFERENCE_DATE.isoformat(), "period": "morning"}).json()
    assert summit["subject"]["canonical_href"] == "/points/tochal"
    assert summit["point"]["href"] == "/points/tochal"
    sarband = api_client.get("/api/v1/points/tochal-sarband-square/forecast/", {"date": REFERENCE_DATE.isoformat(), "period": "morning"}).json()
    assert sarband["subject"]["kind"] == "point"
    assert sarband["subject"]["canonical_href"] == "/points/tochal-sarband-square"
    assert "metrics" in sarband
    assert "decision" in sarband
    routes = {item["slug"] for item in sarband["related_routes"]}
    assert "tochal-darband" in routes


@pytest.mark.django_db
def test_place_forecast_contract_shared_keys(api_client, seeded):
    primary = api_client.get("/api/v1/points/tochal/forecast/", {"date": REFERENCE_DATE.isoformat(), "period": "morning"}).json()
    point = api_client.get("/api/v1/points/tochal-sarband-square/forecast/", {"date": REFERENCE_DATE.isoformat(), "period": "morning"}).json()
    for body in (primary, point):
        assert "subject" in body
        assert body["subject"]["kind"] == "point"
        assert "hero" in body and "status" in body["hero"]
        assert "metrics" in body
        assert [item["icon"] for item in body["metrics"]] == [
            "temperature",
            "temperature",
            "temperature",
            "temperature",
            "precipitation",
            "precipitation",
            "wind-average",
            "wind-gust",
            "visibility",
            "freezing-level",
            "cloud-base",
            "uv-index",
            "precipitation",
            "sunrise-sunset",
        ]
        assert "decision" in body
        assert "related_routes" in body
        forecast = body["forecast"]
        assert set(forecast) >= {"days", "period", "current", "hourly", "meta"}
        assert forecast["period"]["id"] == "morning"
        assert forecast["period"]["planner_step_minutes"] == 60
        assert forecast["meta"]["selected_period"] == "morning"
        # Root aliases remain for compatibility; nested forecast is authoritative.
        assert body["days"] == forecast["days"]
        assert body["meta"]["selected_date"] == forecast["meta"]["selected_date"]
    assert primary["subject"]["weather_point_slug"] == "tochal"
    assert primary["point"]["weather_point_slug"] == "tochal"
    assert primary["related_routes_title"].startswith("مسیرهای منتهی به")
    assert point["related_routes_title"] == "مسیرهای عبوری از این نقطه"

"""Focused tests for adaptive forecast periods and route point detail."""

from __future__ import annotations

from datetime import datetime, timezone as utc_timezone
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


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seeded(db):
    return seed_demo_data(force=True)


@pytest.mark.django_db
def test_parse_period_accepts_three_periods():
    assert parse_period("morning") == "morning"
    assert parse_period("afternoon") == "afternoon"
    assert parse_period("night") == "night"
    assert parse_period(None) == "morning"


@pytest.mark.django_db
def test_default_selection_boundaries():
    tz = timezone()
    cases = [
        (datetime(2026, 8, 28, 0, 30, tzinfo=tz), "2026-08-27", "night"),
        (datetime(2026, 8, 28, 2, 59, tzinfo=tz), "2026-08-27", "night"),
        (datetime(2026, 8, 28, 3, 0, tzinfo=tz), "2026-08-28", "morning"),
        (datetime(2026, 8, 28, 10, 59, tzinfo=tz), "2026-08-28", "morning"),
        (datetime(2026, 8, 28, 11, 0, tzinfo=tz), "2026-08-28", "afternoon"),
        (datetime(2026, 8, 28, 18, 59, tzinfo=tz), "2026-08-28", "afternoon"),
        (datetime(2026, 8, 28, 19, 0, tzinfo=tz), "2026-08-28", "night"),
    ]
    for at, expected_date, expected_period in cases:
        selected_date, period = default_forecast_selection(at)
        assert selected_date.isoformat() == expected_date
        assert period == expected_period


@pytest.mark.django_db
def test_period_windows_do_not_overlap():
    day = datetime(2026, 8, 28).date()
    windows = {name: period_window(day, name) for name in ("morning", "afternoon", "night")}
    morning_end = windows["morning"][1]
    afternoon_start = windows["afternoon"][0]
    afternoon_end = windows["afternoon"][1]
    night_start = windows["night"][0]
    assert morning_end == afternoon_start
    assert afternoon_end == night_start
    assert windows["morning"] == (
        datetime(2026, 8, 28, 3, 0, tzinfo=timezone()),
        datetime(2026, 8, 28, 11, 0, tzinfo=timezone()),
    )
    assert windows["afternoon"] == (
        datetime(2026, 8, 28, 11, 0, tzinfo=timezone()),
        datetime(2026, 8, 28, 19, 0, tzinfo=timezone()),
    )
    assert windows["night"] == (
        datetime(2026, 8, 28, 19, 0, tzinfo=timezone()),
        datetime(2026, 8, 29, 3, 0, tzinfo=timezone()),
    )


@pytest.mark.django_db
def test_destination_forecast_three_periods_and_night_crossing(api_client, seeded):
    day = datetime(2026, 8, 28).date()
    morning = api_client.get("/api/v1/destinations/touchal/forecast/", {"date": day.isoformat(), "period": "morning"}).json()
    afternoon = api_client.get("/api/v1/destinations/touchal/forecast/", {"date": day.isoformat(), "period": "afternoon"}).json()
    night = api_client.get("/api/v1/destinations/touchal/forecast/", {"date": day.isoformat(), "period": "night"}).json()

    assert [item["hour"] for item in morning["hourly"]] == [3, 5, 7, 9]
    assert [item["hour"] for item in afternoon["hourly"]] == [11, 13, 15, 17]
    assert [item["hour"] for item in night["hourly"]] == [19, 21, 23, 1]

    night_times = {item["forecast_at"] for item in night["hourly"]}
    morning_times = {item["forecast_at"] for item in morning["hourly"]}
    afternoon_times = {item["forecast_at"] for item in afternoon["hourly"]}
    assert night_times.isdisjoint(morning_times)
    assert morning_times.isdisjoint(afternoon_times)
    assert afternoon_times.isdisjoint(night_times)

    overnight_one = next(item for item in night["hourly"] if item["hour"] == 1)
    assert overnight_one["forecast_at"].startswith("2026-08-29T01")
    assert overnight_one["forecast_at"].endswith("+03:30")
    assert morning["meta"]["forecast_validity"]["valid_from"].endswith("+03:30")


@pytest.mark.django_db
def test_explicit_query_params_override_defaults(api_client, seeded):
    response = api_client.get(
        "/api/v1/destinations/touchal/forecast/",
        {"date": "2026-08-20", "period": "afternoon"},
    )
    body = response.json()
    assert body["meta"]["selected_date"] == "2026-08-20"
    assert body["meta"]["selected_period"] == "afternoon"


@pytest.mark.django_db
@patch("hawatch.api.v1.views.default_forecast_selection", return_value=(datetime(2026, 8, 28).date(), "morning"))
def test_defaults_applied_without_query_params(mock_default, api_client, seeded):
    body = api_client.get("/api/v1/destinations/touchal/forecast/").json()
    assert body["meta"]["selected_date"] == "2026-08-28"
    assert body["meta"]["selected_period"] == "morning"
    mock_default.assert_called_once()


@pytest.mark.django_db
def test_night_start_minutes_cross_midnight():
    assert parse_start_minutes("00:30", "night", None) == 1470
    assert parse_start_minutes("01:30", "night", None) == 1530
    assert parse_start_minutes("02:30", "night", None) == 1590
    assert parse_start_minutes("03:00", "night", None) == 1590


@pytest.mark.django_db
def test_destination_overnight_current_at_0130(api_client, seeded):
    tz = timezone()
    at = datetime(2026, 8, 28, 1, 30, tzinfo=tz)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get("/api/v1/destinations/touchal/forecast/").json()
    assert body["meta"]["selected_date"] == "2026-08-27"
    assert body["meta"]["selected_period"] == "night"
    assert body["current"] is not None
    assert body["current"]["is_current"] is True
    assert "الان" in body["hero"]["status"]
    yesterday = next(day for day in body["days"] if day["date"] == "2026-08-27")
    assert yesterday["is_past"] is False


@pytest.mark.django_db
def test_destination_default_uses_current_tehran_hour(api_client, seeded):
    tz = timezone()
    at = datetime(2026, 8, 28, 7, 30, tzinfo=tz)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get("/api/v1/destinations/touchal/forecast/").json()

    assert body["meta"]["selected_period"] == "morning"
    assert [item["hour"] for item in body["hourly"]] == [3, 5, 7, 9]
    assert body["current"]["hour"] == 7
    assert body["current"]["is_current"] is True
    assert all(item["is_past"] for item in body["hourly"] if item["hour"] < 7)


@override_settings(TIME_ZONE="UTC")
def test_forecast_clock_stays_on_official_iran_time():
    assert timezone().key == "Asia/Tehran"
    selected_date, period = default_forecast_selection(datetime(2026, 8, 28, 5, 0, tzinfo=utc_timezone.utc))
    assert selected_date.isoformat() == "2026-08-28"
    assert period == "morning"

    flags = datetime_flags(
        datetime(2026, 8, 28, 4, 30, tzinfo=utc_timezone.utc),
        datetime(2026, 8, 28, 5, 0, tzinfo=utc_timezone.utc),
    )
    assert flags["is_current"] is True


@pytest.mark.django_db
def test_current_period_start_minutes_floors_without_crossing_exclusive_end():
    tz = timezone()
    cases = [
        (datetime(2026, 8, 28, 10, 29, tzinfo=tz), "morning", 600),
        (datetime(2026, 8, 28, 10, 45, tzinfo=tz), "morning", 630),
        (datetime(2026, 8, 28, 18, 45, tzinfo=tz), "afternoon", 1110),
        (datetime(2026, 8, 28, 2, 45, tzinfo=tz), "night", 1590),
        (datetime(2026, 8, 28, 11, 0, tzinfo=tz), "afternoon", 660),
        (datetime(2026, 8, 28, 19, 0, tzinfo=tz), "night", 1140),
    ]
    for at, period, expected in cases:
        assert current_period_start_minutes(period, at) == expected


@pytest.mark.django_db
def test_parse_start_minutes_respects_exclusive_period_end():
    assert parse_start_minutes("11:00", "morning", None) == 630
    assert parse_start_minutes("19:00", "afternoon", None) == 1110
    assert parse_start_minutes("03:00", "night", None) == 1590


@pytest.mark.django_db
def test_route_point_forecast_and_missing_data(api_client, seeded):
    today = datetime(2026, 8, 28).date()
    response = api_client.get(
        "/api/v1/routes/touchal-darband/points/shirpala/forecast/",
        {"date": today.isoformat(), "period": "morning"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["point"]["slug"] == "shirpala"
    assert body["point"]["route_slug"] == "touchal-darband"
    assert body["point"]["href"] == "/points/shirpala"
    assert body["canonical_href"] == "/points/shirpala"
    assert body["back_href"].startswith("/routes/touchal-darband?")

    missing = api_client.get("/api/v1/routes/touchal-darband/points/unknown-point/forecast/")
    assert missing.status_code == 404


@pytest.mark.django_db
def test_timing_pending_does_not_invent_arrivals(api_client, seeded):
    today = datetime(2026, 8, 28).date()
    body = api_client.get(
        "/api/v1/routes/touchal-darband/forecast/",
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
def test_timing_pending_point_weather_stays_in_selected_period(api_client, seeded):
    tz = timezone()
    at = datetime(2026, 8, 28, 10, 30, tzinfo=tz)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get(
            "/api/v1/routes/touchal-darband/forecast/",
            {"date": "2026-08-28", "period": "night"},
        ).json()
    assert body["timing_pending"] is True
    allowed_hours = {19, 21, 23, 1}
    for point in body["points"]:
        if point["weather_available"]:
            assert point["weather"]["hour"] in allowed_hours
        else:
            assert point["condition"] == "در دسترس نیست"


@pytest.mark.django_db
def test_tochal_summit_canonical_href(api_client, seeded):
    body = api_client.get(
        "/api/v1/routes/touchal-darband/points/tochal_summit/forecast/",
        {"date": "2026-08-28", "period": "morning"},
    ).json()
    assert body["canonical_href"] == "/destination/touchal"
    assert body["point"]["href"] == "/destination/touchal"


@pytest.mark.django_db
def test_route_default_start_uses_current_tehran_in_current_period(api_client, seeded):
    tz = timezone()
    at = datetime(2026, 8, 28, 7, 30, tzinfo=tz)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get(
            "/api/v1/routes/touchal-darband/forecast/",
            {"date": "2026-08-28", "period": "morning"},
        ).json()
    assert body["start_minutes"] == 450


@pytest.mark.django_db
def test_destination_night_period_uses_in_window_reading_at_1030(api_client, seeded):
    tz = timezone()
    at = datetime(2026, 8, 28, 10, 30, tzinfo=tz)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get(
            "/api/v1/destinations/touchal/forecast/",
            {"date": "2026-08-28", "period": "night"},
        ).json()
    allowed_hours = {19, 21, 23, 1}
    assert body["current"] is not None
    assert body["current"]["hour"] in allowed_hours
    assert body["current"]["is_current"] is False
    assert "الان" not in body["hero"]["status"]
    assert all(item["hour"] in allowed_hours for item in body["hourly"])


@pytest.mark.django_db
def test_point_night_period_uses_in_window_reading_at_1030(api_client, seeded):
    tz = timezone()
    at = datetime(2026, 8, 28, 10, 30, tzinfo=tz)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get(
            "/api/v1/points/shirpala/forecast/",
            {"date": "2026-08-28", "period": "night"},
        ).json()
    allowed_hours = {19, 21, 23, 1}
    assert body["current"] is not None
    assert body["weather"]["hour"] in allowed_hours
    assert body["weather"]["is_current"] is False
    assert "الان" not in body["hero"]["status"]


@pytest.mark.django_db
def test_point_overnight_current_at_0130(api_client, seeded):
    tz = timezone()
    at = datetime(2026, 8, 28, 1, 30, tzinfo=tz)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        body = api_client.get("/api/v1/points/shirpala/forecast/").json()
    assert body["meta"]["selected_date"] == "2026-08-27"
    assert body["meta"]["selected_period"] == "night"
    assert body["current"]["is_current"] is True
    assert body["current"]["hour"] == 1
    assert "الان" in body["hero"]["status"]


@pytest.mark.django_db
def test_route_period_switch_uses_period_default_not_route_default(api_client, seeded):
    tz = timezone()
    at = datetime(2026, 8, 28, 10, 30, tzinfo=tz)
    with patch("hawatch.api.v1.views.now_tehran", return_value=at), patch(
        "hawatch.api.v1.serializers.now_tehran", return_value=at
    ):
        afternoon = api_client.get(
            "/api/v1/routes/touchal-darband/forecast/",
            {"date": "2026-08-28", "period": "afternoon"},
        ).json()
        night = api_client.get(
            "/api/v1/routes/touchal-darband/forecast/",
            {"date": "2026-08-28", "period": "night"},
        ).json()
    assert afternoon["start_minutes"] == 720
    assert night["start_minutes"] == 1200


@pytest.mark.django_db
def test_route_start_time_floors_off_step_minutes(api_client, seeded):
    body = api_client.get(
        "/api/v1/routes/touchal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "10:15"},
    ).json()
    assert body["start_minutes"] == 600


@pytest.mark.django_db
def test_normalize_start_minutes_floors_persian_digits():
    assert normalize_start_minutes("۱۰:۱۵", "morning") == 600
    assert resolve_planner_start_minutes(
        datetime(2026, 8, 28).date(),
        "afternoon",
        local=datetime(2026, 8, 28, 10, 30, tzinfo=timezone()),
        raw_start="12:15",
    ) == 720


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
    assert normalize_start_minutes("90", "night") == 1530


@pytest.mark.django_db
def test_route_invalid_start_time_returns_400(api_client, seeded):
    response = api_client.get(
        "/api/v1/routes/touchal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "12:xx"},
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_start_time_wire_format_is_ascii():
    assert format_start_time_wire(360) == "06:00"
    assert format_start_time_wire(720) == "12:00"

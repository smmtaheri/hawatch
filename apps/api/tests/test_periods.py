"""Focused tests for adaptive forecast periods and route point detail."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from hawatch.common.time import (
    default_forecast_selection,
    parse_period,
    parse_start_minutes,
    period_window,
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
    from hawatch.common.time import timezone

    tz = timezone()
    cases = [
        (datetime(2026, 8, 28, 0, 30, tzinfo=tz), "2026-08-27", "night"),
        (datetime(2026, 8, 28, 2, 0, tzinfo=tz), "2026-08-28", "morning"),
        (datetime(2026, 8, 28, 9, 59, tzinfo=tz), "2026-08-28", "morning"),
        (datetime(2026, 8, 28, 10, 0, tzinfo=tz), "2026-08-28", "afternoon"),
        (datetime(2026, 8, 28, 17, 59, tzinfo=tz), "2026-08-28", "afternoon"),
        (datetime(2026, 8, 28, 18, 0, tzinfo=tz), "2026-08-28", "night"),
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


@pytest.mark.django_db
def test_destination_forecast_three_periods_and_night_crossing(api_client, seeded):
    day = datetime(2026, 8, 28).date()
    morning = api_client.get("/api/v1/destinations/touchal/forecast/", {"date": day.isoformat(), "period": "morning"}).json()
    afternoon = api_client.get("/api/v1/destinations/touchal/forecast/", {"date": day.isoformat(), "period": "afternoon"}).json()
    night = api_client.get("/api/v1/destinations/touchal/forecast/", {"date": day.isoformat(), "period": "night"}).json()

    assert [item["hour"] for item in morning["hourly"]] == [2, 4, 6, 8]
    assert [item["hour"] for item in afternoon["hourly"]] == [10, 12, 14, 16]
    assert [item["hour"] for item in night["hourly"]] == [18, 20, 22, 0]

    night_times = {item["forecast_at"] for item in night["hourly"]}
    morning_times = {item["forecast_at"] for item in morning["hourly"]}
    assert night_times.isdisjoint(morning_times)

    midnight = next(item for item in night["hourly"] if item["hour"] == 0)
    assert midnight["forecast_at"].startswith("2026-08-29T00")


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
    assert body["point"]["href"].startswith("/routes/touchal-darband/points/")
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

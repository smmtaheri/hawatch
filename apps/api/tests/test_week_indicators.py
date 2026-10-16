"""Hourly-source interval indicators; no database/provider is needed to aggregate."""
from datetime import date, timedelta
import json
from types import SimpleNamespace
from unittest.mock import patch
import zlib

import pytest
from django.core.cache import cache
from django.test import override_settings

from hawatch.api.v1.week_bundles import aggregate
from hawatch.api.v1.week_views import cached_week
from hawatch.common.time import localize_dt
from hawatch.integrations.weather.hazards import assess, assess_records, heat_index

START = localize_dt(date(2026, 10, 16), 0)


def readings(hours=25, **overrides):
    return [SimpleNamespace(
        forecast_at=START+timedelta(hours=i), valid_from=START+timedelta(hours=i),
        valid_to=START+timedelta(hours=i+1),
        **(dict(temperature_c=20, apparent_temperature_c=19,
                relative_humidity_pct=50, uv_index=0, wind_speed_kmh=10,
                wind_gust_kmh=15, wind_direction_deg=0, precipitation_mm=0,
                snowfall_cm=0, visibility_km=10, freezing_level_m=3000,
                weather_code="clear", condition_label="صاف", wmo_code=0,
                fields_unavailable=[]) | overrides),
    ) for i in range(hours)]


@pytest.mark.parametrize("hours", [24, 6, 3, 1])
def test_extrema_and_uv_use_only_their_own_half_open_interval(hours):
    rows = readings()
    for i, row in enumerate(rows):
        row.temperature_c = i-12
        row.apparent_temperature_c = i-15
        row.uv_index = i
    result = aggregate(rows, START, hours)
    assert result["min"] == -12 and result["max"] == hours-13
    assert result["felt_min"] == -15 and result["felt_max"] == hours-16
    assert result["min"] <= result["actual"] <= result["max"]
    assert result["felt_min"] <= result["felt"] <= result["felt_max"]
    assert result["uv_index"] == hours-1  # The endpoint reading is excluded.


def test_incomplete_fields_are_independent_and_uv_zero_is_real():
    rows = readings(7)
    rows[2].fields_unavailable = ["apparent_temperature_c", "uv_index"]
    result = aggregate(rows, START, 6)
    assert result["felt_min"] is None and result["felt_max"] is None
    assert result["uv_index"] is None
    assert result["min"] == 20 and result["rain"] == 0
    assert aggregate(rows, START, 1)["uv_index"] == 0
    rows[2].fields_unavailable = []
    rows[2].uv_index = -1
    assert aggregate(rows, START, 6)["uv_index"] is None
    # Missing rain at the right endpoint does not discard valid temperatures.
    result = aggregate(rows[:-1], START, 6)
    assert result["min"] == 20 and result["rain"] is None


def test_heat_is_peak_of_simultaneous_hourly_inputs_not_mean_inputs():
    rows = readings(7)
    rows[3].temperature_c = 35
    rows[3].relative_humidity_pct = 60
    assess_records(rows)
    result = aggregate(rows, START, 6)
    assert result["heat_index_status"] == "available"
    assert result["heat_index_c"] == round(heat_index(35, 60), 1)
    assert heat_index(result["actual"], result["humidity"]) is None
    warning=next(w for w in result["warnings"] if w["code"]=="heat")
    assert warning["severity"]=="critical"
    assert warning["metrics"]==["heat_index_c"]


@pytest.mark.parametrize("field,bad", [("temperature_c", None), ("relative_humidity_pct", None), ("relative_humidity_pct", 101)])
def test_missing_heat_inputs_never_produce_a_definitive_peak(field, bad):
    rows = readings(7, temperature_c=35, relative_humidity_pct=60)
    setattr(rows[2], field, bad)
    result = aggregate(rows, START, 6)
    assert result["heat_index_c"] is None and result["heat_index_status"] == "missing"


def test_cool_hours_are_not_missing_and_missing_hours_are_not_cool():
    rows = readings(7)
    result = aggregate(rows, START, 6)
    assert result["heat_index_c"] is None and result["heat_index_status"] == "not_applicable"
    rows[2].fields_unavailable = ["relative_humidity_pct"]
    assert aggregate(rows, START, 6)["heat_index_status"] == "missing"
    assert aggregate(rows[:5], START, 6)["heat_index_status"] == "missing"
    assert aggregate([], START, 6)["heat_index_status"] == "missing"


@pytest.mark.parametrize("value,reported,severity", [(31.96,31.9,"normal"), (32,32,"change"), (39.9,39.9,"change"), (39.96,39.9,"change"), (40,40,"critical")])
def test_reported_heat_never_rounds_across_its_shared_warning_boundary(value, reported, severity):
    with patch("hawatch.integrations.weather.hazards.heat_index", return_value=value):
        risk = assess(readings(1)[0])
    assert risk["heat_index_c"] == reported
    assert risk["severity"] == severity


def test_cached_hourly_assessments_are_reused_for_every_resolution():
    rows = assess_records(readings())
    with patch("hawatch.integrations.weather.hazards.assess", side_effect=AssertionError("recomputed")):
        for hours in (24, 6, 3, 1):
            assert aggregate(rows, START, hours)["heat_index_status"] == "not_applicable"


@pytest.mark.parametrize("kind", ["point", "route"])
@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
def test_old_heat_metric_binding_is_not_reused_from_week_cache(kind):
    today=START.date()
    previous={"warnings": [{"metrics": ["temperature_c","heat_index_c"]}]}
    current={"last_generated_at": START.isoformat(),"warnings": [{"metrics": ["heat_index_c"]}]}
    cache.clear()
    try:
        cache.set(f"week-9:fixed:{kind}:tochal:{today}", (zlib.compress(json.dumps(previous).encode()), '"old"'))
        with patch("hawatch.api.v1.week_views.revision",return_value="fixed"), patch("hawatch.api.v1.week_views.build_week",return_value=current) as build:
            (body,_),status=cached_week(kind,"tochal",today)
            assert status=="MISS" and json.loads(body)==current
            assert cached_week(kind,"tochal",today)[1]=="HIT"
            build.assert_called_once()
    finally:
        cache.clear()

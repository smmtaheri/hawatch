from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from hawatch.integrations.weather.hazards import (
    assess, assess_records, assessment, heat_index, representative_record,
    warning_intervals, wind_chill,
)
from hawatch.integrations.weather.normalize import normalize_point_hourly

AT = datetime(2026, 10, 2, 10, tzinfo=timezone.utc)


def row(at=AT, **kwargs):
    fields = dict(forecast_at=at, valid_from=at, valid_to=at+timedelta(hours=1),
                  temperature_c=15, apparent_temperature_c=15,
                  wind_speed_kmh=10, wind_gust_kmh=20, weather_code="overcast",
                  wmo_code=3, relative_humidity_pct=50, precipitation_mm=0,
                  rain_mm=0, snowfall_cm=0, visibility_km=10, fields_unavailable=[],
                  severity="critical")
    return SimpleNamespace(**(fields | kwargs))


@pytest.mark.parametrize("wind,gust,severity", [(29,49,"normal"),(30,49,"change"),
    (29,80,"normal"),(30,80,"change"),(44.9,100,"change"),(45,79,"critical"),
    (20,100,"normal"),(None,100,"normal"),(45,None,"critical")])
def test_exact_wind_boundaries(wind,gust,severity):
    assert assess(row(wind_speed_kmh=wind,wind_gust_kmh=gust))["severity"] == severity


@pytest.mark.parametrize("code,wmo", [("overcast",3),("drizzle",53),("rain",63),
                                       ("snow",71),("shower",80)])
def test_sky_name_and_old_critical_do_not_create_a_warning(code,wmo):
    assert assess(row(weather_code=code,wmo_code=wmo,precipitation_mm=.2,snowfall_cm=.1))["severity"] == "normal"


def test_lightning_is_red_even_without_wind_or_rain():
    risk = assess(row(weather_code="thunder",wmo_code=95))
    assert risk["severity"] == "critical"
    assert risk["warnings"][0]["metrics"] == []


def test_gust_severity_follows_mean_wind_and_never_overrides_it():
    assert not assess(row(wind_gust_kmh=100))["warnings"]
    risk = assess(row(wind_speed_kmh=30, wind_gust_kmh=100))
    assert risk["warnings"][0]["metric_severities"] == {
        "wind_speed_kmh": "change", "wind_gust_kmh": "change",
    }
    risk = assess(row(wind_speed_kmh=45, wind_gust_kmh=80))
    assert risk["warnings"][0]["metric_severities"] == {
        "wind_speed_kmh": "critical", "wind_gust_kmh": "critical",
    }


@pytest.mark.parametrize("temp,severity", [(-9,"normal"),(-10,"change"),(-27,"change"),(-28,"critical")])
def test_cold_threshold_is_wind_chill_not_apparent_temperature(temp,severity):
    assert assess(row(temperature_c=temp, apparent_temperature_c=-50, wind_speed_kmh=0))["severity"] == severity


def test_wind_chill_and_heat_are_independent_indices():
    assert wind_chill(0,20) == pytest.approx(-5.242,abs=.01)
    assert wind_chill(20,50) is None
    assert heat_index(35,None) is None
    assert heat_index(35,60) > 40
    assert any(w["code"] == "heat" and w["severity"] == "critical" for w in assess(row(temperature_c=35, relative_humidity_pct=60))["warnings"])


def test_wet_cold_requires_contiguous_two_hours():
    first=row(temperature_c=8,wind_speed_kmh=20,precipitation_mm=1)
    second=row(AT+timedelta(hours=1),temperature_c=8,wind_speed_kmh=20,precipitation_mm=1)
    assert not assess(first)["warnings"]
    assess_records([first,second])
    assert assessment(first)["warnings"][0]["code"] == "wet_cold"
    second.forecast_at += timedelta(hours=1)
    assert not assess(first,[first,second])["warnings"]


def test_rain_persistence_and_snow_totals_require_real_coverage():
    rain=[row(AT+timedelta(hours=i),precipitation_mm=5) for i in range(3)]
    assert not assess(rain[0],rain[:2])["warnings"]
    assert all(any(w["code"]=="rain" for w in assess(r,rain)["warnings"]) for r in rain)
    snow=[row(AT+timedelta(hours=i),snowfall_cm=.625) for i in range(24)]
    assert not assess(snow[-1],snow[1:])["warnings"]
    assert any(w["code"]=="snow" for w in assess(snow[-1],snow)["warnings"])


def test_compound_snow_wind_visibility_is_red_without_claiming_avalanche():
    risk=assess(row(snowfall_cm=1,wind_speed_kmh=50,visibility_km=.05))
    assert any(w["code"]=="snow_wind_visibility" and w["severity"]=="critical" for w in risk["warnings"])
    assert not any(w["code"] in ("avalanche","flood") for w in risk["warnings"])


def test_missing_inputs_do_not_become_safe_values():
    risk=assess(row(fields_unavailable=["visibility_km","wind_gust_kmh"],wind_gust_kmh=99))
    assert risk["severity"] == "normal"
    assert risk["data_quality"] == "partial"
    assert set(risk["missing_inputs"]) == {"visibility_km","wind_gust_kmh"}


def test_daily_intervals_merge_only_adjacent_hours_and_omit_elapsed_today():
    rows=assess_records([row(AT+timedelta(hours=i),wind_speed_kmh=35,wind_gust_kmh=60) for i in (0,1,3)])
    intervals=warning_intervals(rows)
    assert len(intervals)==2
    assert intervals[0]["end_at"]==(AT+timedelta(hours=2)).isoformat()
    assert len(warning_intervals(rows,now=AT+timedelta(hours=2)))==1


def test_daily_weather_is_representative_not_worst_hour():
    rows=[row(weather_code="thunder",wmo_code=95),row(),row()]
    assert representative_record(rows).weather_code == "overcast"


def test_normalizer_preserves_raw_code_and_never_invents_visibility_or_humidity():
    payload={"hourly":{"time":["2026-10-02T10:00"],"temperature_2m":[15],"apparent_temperature":[15]}}
    result=normalize_point_hourly(payload,generated_at=AT)[0]
    assert result["wmo_code"] is None
    assert result["relative_humidity_pct"] is None
    assert result["weather_code"]=="unknown"
    assert "visibility_km" in result["fields_unavailable"]
    assert result["severity"]=="normal"

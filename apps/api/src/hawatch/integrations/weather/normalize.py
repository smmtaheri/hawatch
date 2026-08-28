"""Normalize Open-Meteo hourly payloads into ForecastRecord-ready rows."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import asin, cos, isfinite, radians, sin, sqrt
from typing import Any
from zoneinfo import ZoneInfo

from hawatch.integrations.weather.schemas import NormalizedReading

TEHRAN = ZoneInfo("Asia/Tehran")
MAX_PROVIDER_RESOLUTION_DISTANCE_KM = 5.0

# Fields intentionally not requested from Open-Meteo in this vertical slice.
UNAVAILABLE_HOURLY_FIELDS = ("cloud_cover_pct", "uv_index", "freezing_level_m", "cloud_base_m")

# WMO weather interpretation codes → UI condition/icon/severity.
WMO_MAP: dict[int, tuple[str, str, str, str]] = {
    0: ("clear", "صاف", "☼", "normal"),
    1: ("mainly-clear", "عمدتاً صاف", "☼", "normal"),
    2: ("partly-cloudy", "نیمه‌ابری", "◒", "normal"),
    3: ("overcast", "ابری", "☁", "change"),
    45: ("fog", "مه", "☁", "change"),
    48: ("fog", "مه یخ‌زده", "☁", "change"),
    51: ("drizzle", "نم‌نم باران", "☂", "change"),
    53: ("drizzle", "نم‌نم باران", "☂", "change"),
    55: ("drizzle", "نم‌نم باران", "☂", "critical"),
    56: ("freezing-drizzle", "نم‌نم یخ‌زده", "☂", "critical"),
    57: ("freezing-drizzle", "نم‌نم یخ‌زده", "☂", "critical"),
    61: ("rain", "باران", "☂", "change"),
    63: ("rain", "باران", "☂", "critical"),
    65: ("rain", "باران شدید", "☂", "critical"),
    66: ("freezing-rain", "باران یخ‌زده", "☂", "critical"),
    67: ("freezing-rain", "باران یخ‌زده", "☂", "critical"),
    71: ("snow", "برف", "❄", "critical"),
    73: ("snow", "برف", "❄", "critical"),
    75: ("snow", "برف شدید", "❄", "critical"),
    77: ("snow", "دانه‌برف", "❄", "critical"),
    80: ("shower", "رگبار", "☂", "critical"),
    81: ("shower", "رگبار", "☂", "critical"),
    82: ("shower", "رگبار شدید", "☂", "critical"),
    85: ("snow", "رگبار برف", "❄", "critical"),
    86: ("snow", "رگبار برف", "❄", "critical"),
    95: ("thunder", "رعدوبرق", "⚡", "critical"),
    96: ("thunder", "رعدوبرق با تگرگ", "⚡", "critical"),
    99: ("thunder", "رعدوبرق با تگرگ", "⚡", "critical"),
}


def map_weather_code(code: int | float | None, *, hour: int, wind_kmh: int, gust_kmh: int) -> tuple[str, str, str, str]:
    """Map the provider sky condition without hiding it behind a wind warning.

    Wind is a separate hazard from the WMO sky/precipitation code.  Keep the
    latter as the condition shown to users, while still escalating severity so
    route and decision cards can warn about strong wind.
    """
    raw = int(code or 0)
    weather_code, label, icon, severity = WMO_MAP.get(raw, ("unknown", "نامشخص", "◒", "change"))
    if raw == 0 and hour >= 19:
        weather_code, label, icon = "clear-night", "صاف", "☾"

    if wind_kmh >= 30 or gust_kmh >= 40:
        severity = "critical"
    elif wind_kmh >= 22 and severity == "normal":
        severity = "change"
    return weather_code, label, icon, severity


def parse_local_time(value: str, *, fallback_tz: ZoneInfo = TEHRAN) -> datetime:
    # Open-Meteo iso8601 without offset when timezone=Asia/Tehran: "2026-08-21T15:00"
    if value.endswith("Z"):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(fallback_tz)
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=fallback_tz)
    return dt.astimezone(fallback_tz)


def normalize_point_hourly(
    raw_point: dict[str, Any],
    *,
    generated_at: datetime,
) -> list[dict[str, Any]]:
    hourly = raw_point.get("hourly") or {}
    times = hourly.get("time") or []
    rows: list[dict[str, Any]] = []
    for index, stamp in enumerate(times):
        forecast_at = parse_local_time(stamp)
        temp = _num(hourly.get("temperature_2m"), index, default=0.0)
        apparent = _num(hourly.get("apparent_temperature"), index, default=temp)
        precip_prob = int(round(_num(hourly.get("precipitation_probability"), index, default=0.0)))
        precip_mm = _num(hourly.get("precipitation"), index, default=0.0)
        snowfall = _num(hourly.get("snowfall"), index, default=0.0)
        code = _num(hourly.get("weather_code"), index, default=0.0)
        visibility_m = _num(hourly.get("visibility"), index, default=10000.0)
        wind = int(round(_num(hourly.get("wind_speed_10m"), index, default=0.0)))
        gust = int(round(_num(hourly.get("wind_gusts_10m"), index, default=float(wind))))
        direction = int(round(_num(hourly.get("wind_direction_10m"), index, default=0.0))) % 360
        weather_code, label, icon, severity = map_weather_code(code, hour=forecast_at.hour, wind_kmh=wind, gust_kmh=gust)
        # Never invent cloud cover / UV — leave unavailable when not provided by the provider payload.
        cloud_cover = _optional_int(hourly.get("cloud_cover"), index)
        uv_index = _optional_int(hourly.get("uv_index"), index)
        reading: NormalizedReading = {
            "temperature_c": int(round(temp)),
            "apparent_temperature_c": int(round(apparent)),
            "weather_code": weather_code,
            "condition_label": label,
            "icon": icon,
            "wind_speed_kmh": max(0, wind),
            "wind_gust_kmh": max(0, gust),
            "wind_direction_deg": direction,
            "precipitation_probability": max(0, min(100, precip_prob)),
            "precipitation_mm": round(max(0.0, precip_mm), 1),
            "visibility_km": round(max(0.0, visibility_m / 1000.0), 1),
            "cloud_cover_pct": cloud_cover,
            "uv_index": uv_index,
            "freezing_level_m": None,
            "cloud_base_m": None,
            "severity": severity,
        }
        interval_end = forecast_at + timedelta(hours=1)
        rows.append(
            {
                "forecast_at": forecast_at,
                "valid_from": forecast_at,
                "valid_to": interval_end,
                "generated_at": generated_at,
                "snowfall_cm": round(max(0.0, snowfall), 1),
                "wmo_code": int(code),
                "fields_unavailable": [
                    field
                    for field, value in (
                        ("cloud_cover_pct", cloud_cover),
                        ("uv_index", uv_index),
                        ("freezing_level_m", None),
                        ("cloud_base_m", None),
                    )
                    if value is None
                ],
                **reading,
            }
        )
    return rows


def extract_resolution(raw_point: dict[str, Any]) -> dict[str, Any]:
    return {
        "resolved_latitude": raw_point.get("latitude"),
        "resolved_longitude": raw_point.get("longitude"),
        "resolved_elevation_m": raw_point.get("elevation"),
        "utc_offset_seconds": raw_point.get("utc_offset_seconds"),
        "generationtime_ms": raw_point.get("generationtime_ms"),
        "timezone_abbreviation": raw_point.get("timezone_abbreviation") or "",
    }


def response_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        # Never silently drop a malformed item: the caller relies on positional
        # correspondence between requested points and provider responses.
        return payload if all(isinstance(item, dict) for item in payload) else []
    if isinstance(payload, dict) and "hourly" in payload:
        return [payload]
    return []


def provider_resolution_distance_km(
    raw_point: dict[str, Any],
    *,
    requested_latitude: float,
    requested_longitude: float,
) -> float | None:
    """Return the WGS84 distance to Open-Meteo's resolved grid-cell center.

    Open-Meteo returns the selected grid cell's coordinates, not necessarily the
    exact requested coordinate.  A missing or invalid resolution cannot be
    safely associated with a catalog point and therefore returns ``None``.
    """
    try:
        resolved_latitude = float(raw_point["latitude"])
        resolved_longitude = float(raw_point["longitude"])
        requested_latitude = float(requested_latitude)
        requested_longitude = float(requested_longitude)
    except (KeyError, TypeError, ValueError):
        return None
    if not all(
        isfinite(value)
        for value in (
            resolved_latitude,
            resolved_longitude,
            requested_latitude,
            requested_longitude,
        )
    ):
        return None
    if not (-90 <= resolved_latitude <= 90 and -90 <= requested_latitude <= 90):
        return None
    if not (-180 <= resolved_longitude <= 180 and -180 <= requested_longitude <= 180):
        return None

    earth_radius_km = 6371.0088
    lat1, lat2 = radians(requested_latitude), radians(resolved_latitude)
    delta_lat = radians(resolved_latitude - requested_latitude)
    delta_lon = radians(resolved_longitude - requested_longitude)
    haversine = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return earth_radius_km * 2 * asin(sqrt(min(1.0, haversine)))


def provider_resolution_is_acceptable(
    raw_point: dict[str, Any],
    *,
    requested_latitude: float,
    requested_longitude: float,
    max_distance_km: float = MAX_PROVIDER_RESOLUTION_DISTANCE_KM,
) -> bool:
    distance = provider_resolution_distance_km(
        raw_point,
        requested_latitude=requested_latitude,
        requested_longitude=requested_longitude,
    )
    return distance is not None and distance <= max_distance_km


def _num(series: Any, index: int, *, default: float) -> float:
    if not isinstance(series, list) or index >= len(series) or series[index] is None:
        return default
    try:
        return float(series[index])
    except (TypeError, ValueError):
        return default


def _optional_int(series: Any, index: int) -> int | None:
    if not isinstance(series, list) or index >= len(series) or series[index] is None:
        return None
    try:
        return int(round(float(series[index])))
    except (TypeError, ValueError):
        return None

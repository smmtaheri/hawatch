"""Normalized forecast record shape used by the internal API."""

from __future__ import annotations

from typing import TypedDict


class NormalizedReading(TypedDict):
    temperature_c: int
    apparent_temperature_c: int
    weather_code: str
    condition_label: str
    icon: str
    wind_speed_kmh: int
    wind_gust_kmh: int
    wind_direction_deg: int
    precipitation_probability: int
    precipitation_mm: float
    visibility_km: float
    cloud_cover_pct: int | None
    uv_index: int | None
    freezing_level_m: int | None
    cloud_base_m: int | None
    severity: str

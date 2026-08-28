"""Demo weather generator.

Values are deterministic for a given seed version, point slug, local date, and hour.
They change when the Asia/Tehran date or hour bucket changes.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from pathlib import Path

from django.conf import settings

from hawatch.integrations.weather.schemas import NormalizedReading

WIND_LABELS = {
    0: "شمال",
    45: "شمال‌شرقی",
    90: "شرق",
    135: "جنوب‌شرقی",
    180: "جنوب",
    225: "جنوب‌غربی",
    270: "غرب",
    315: "شمال‌غربی",
}


def _profiles() -> dict:
    path = Path(settings.FIXTURES_DIR) / "weather" / "climate_profiles.json"
    return json.loads(path.read_text(encoding="utf-8"))


def unit(seed: str) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def seed_key(*parts: object) -> str:
    version = getattr(settings, "DEMO_SEED_VERSION", "hawatch-demo-v1")
    return "|".join([version, *[str(part) for part in parts]])


def wind_compass(deg: int) -> str:
    bucket = int((deg + 22.5) // 45) * 45 % 360
    return WIND_LABELS[bucket]


def generate_reading(
    *,
    point_slug: str,
    climate_key: str,
    elevation_m: int,
    local_date: date,
    hour: int,
) -> NormalizedReading:
    profiles = _profiles()
    climate = profiles[climate_key]
    base = seed_key(point_slug, local_date.isoformat(), hour)
    u1, u2, u3, u4 = unit(base + "|a"), unit(base + "|b"), unit(base + "|c"), unit(base + "|d")

    day_shift = [-1, 0, 1, 2, 0, -2, -1][local_date.toordinal() % 7]
    diurnal = 4.2 * math.sin(((hour - 5) / 24) * 2 * math.pi)
    lapse = -0.006 * (elevation_m - climate["ref_elevation_m"])
    heat_boost = 6 if climate.get("heat") and 11 <= hour <= 16 else 0
    temp = round(climate["base_temp_c"] + diurnal + lapse + day_shift + (u1 - 0.5) * 2 + heat_boost)
    apparent = temp - (2 if hour < 8 or hour > 18 else 0) + (1 if climate.get("heat") else 0)

    wind = round(climate["base_wind_kmh"] + (climate["afternoon_wind_boost"] if hour >= 11 else 0) * ((hour - 10) / 10 if hour >= 11 else 0.15) + u2 * 6)
    wind = max(3, wind)
    gust = round(wind + 8 + u3 * 12)

    precip_hour = climate.get("precip_after_hour", 99)
    precip_prob = 0
    if hour >= precip_hour - 1:
        precip_prob = min(80, 15 + (hour - precip_hour + 2) * 12 + int(u4 * 10))
    if climate.get("foggy") and hour >= 11:
        precip_prob = max(precip_prob, 25)

    snow = bool(climate.get("snow_possible")) and temp <= 2 and precip_prob >= 20
    fog = bool(climate.get("foggy")) and hour >= 11
    shower = precip_prob >= 35 and not snow
    windy = wind >= 22
    cloudy = precip_prob >= 15 or fog or hour in {5, 7}

    if snow:
        code, label, icon = "snow", "برف", "❄"
        severity = "critical"
    elif shower:
        code, label, icon = "shower", "رگبار پراکنده", "☂"
        severity = "critical"
    elif fog and hour >= 13:
        code, label, icon = "fog", "دید محدود", "☁"
        severity = "critical"
    elif wind >= 30 or gust >= 36:
        code, label, icon = "gale", "تندباد", "≋"
        severity = "critical"
    elif windy:
        code, label, icon = "windy", "بادخیز", "≋"
        severity = "change"
    elif cloudy:
        code, label, icon = "partly-cloudy", "نیمه‌ابری", "◒"
        severity = "change" if precip_prob >= 20 else "normal"
    elif hour >= 19:
        code, label, icon = "clear-night", "سرد و ابری" if cloudy else "صاف", "☾"
        severity = "normal"
    elif climate.get("heat") and hour >= 11:
        code, label, icon = "hot", "گرم", "☼"
        severity = "change" if hour >= 11 else "normal"
    else:
        code, label, icon = "clear", "صاف", "☼"
        severity = "normal"

    if climate.get("heat") and hour >= 15:
        severity = "critical"
        label = "باد شن‌زا"
        icon = "≋"
        code = "sand"

    visibility = float(climate["visibility_km"])
    if fog or snow or shower:
        visibility = max(1.0, visibility * 0.35)
    cloud = 70 if cloudy or snow or fog else 18 if hour in {5, 7} else 8
    uv = 0 if hour < 6 or hour > 18 else int(climate["uv_index"] * (1 if 10 <= hour <= 14 else 0.6))
    freezing = max(0, elevation_m + (4250 - 3964) + int((u1 - 0.5) * 200)) if climate.get("snow_possible") else None
    cloud_base = elevation_m + (400 if not cloudy else -80)

    wind_dir = int(unit(base + "|dir") * 360) % 360

    return {
        "temperature_c": temp,
        "apparent_temperature_c": apparent,
        "weather_code": code,
        "condition_label": label,
        "icon": icon,
        "wind_speed_kmh": int(wind),
        "wind_gust_kmh": int(gust),
        "wind_direction_deg": wind_dir,
        "precipitation_probability": int(precip_prob),
        "precipitation_mm": round(precip_prob / 25, 1) if precip_prob else 0.0,
        "visibility_km": round(visibility, 1),
        "cloud_cover_pct": int(cloud),
        "uv_index": max(0, uv),
        "freezing_level_m": freezing,
        "cloud_base_m": cloud_base,
        "severity": severity,
    }

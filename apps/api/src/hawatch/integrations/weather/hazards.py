"""Versioned public walking policy; independent of sky icons and stored severity.

Terrain-dependent flood/avalanche/exposure rules are deliberately not inferred
from elevation, month or the legacy demo climate. See docs/weather-warnings.md.
"""
from collections import Counter
from datetime import timedelta
from math import isfinite, sqrt

POLICY_VERSION = "walking-v1"
RANK = {"normal": 0, "change": 1, "critical": 2}
CORE_FIELDS = ("temperature_c", "wind_speed_kmh", "wind_gust_kmh",
               "precipitation_mm", "snowfall_cm", "visibility_km")
WIND_LIMITS = {"wind_speed_kmh": (30, 50), "wind_gust_kmh": (50, 80)}


def wind_severity(wind, gust):
    levels = ["critical" if number >= red else "change" if number >= yellow else "normal"
              for number, (yellow, red) in ((wind, WIND_LIMITS["wind_speed_kmh"]),
                                          (gust, WIND_LIMITS["wind_gust_kmh"]))
              if number is not None]
    return max(levels, key=RANK.get, default="normal")


def value(row, field):
    if field in (getattr(row, "fields_unavailable", None) or []):
        return None
    raw = getattr(row, field, None)
    try:
        number = float(raw)
        return number if isfinite(number) else None
    except (ValueError, TypeError):
        return None


def wind_chill(temperature, wind):
    if temperature is None or wind is None or temperature > 10:
        return None
    if wind <= 4.8:
        return temperature
    return 13.12 + .6215 * temperature - 11.37 * wind ** .16 + .3965 * temperature * wind ** .16


def heat_index(temperature, humidity):
    """NWS Rothfusz regression, including low/high humidity adjustments."""
    if temperature is None or humidity is None or not 0 <= humidity <= 100:
        return None
    t = temperature * 9 / 5 + 32
    simple = .5 * (t + 61 + (t - 68) * 1.2 + humidity * .094)
    if (simple + t) / 2 < 80:
        return None
    h = humidity
    result = (-42.379 + 2.04901523*t + 10.14333127*h - .22475541*t*h
              - .00683783*t*t - .05481717*h*h + .00122874*t*t*h
              + .00085282*t*h*h - .00000199*t*t*h*h)
    if h < 13 and 80 <= t <= 112:
        result -= (13-h)/4 * sqrt((17-abs(t-95))/17)
    elif h > 85 and 80 <= t <= 87:
        result += (h-85)/10 * (87-t)/5
    return (result - 32) * 5 / 9


def assess(row, records=(), *, _by_at=None):
    warnings = []
    def add(code, label, severity, metrics, reason):
        warnings.append({"code": code, "label": label, "severity": severity,
                         "metrics": metrics, "reason": reason,
                         "start_at": row.valid_from.isoformat(), "end_at": row.valid_to.isoformat(),
                         "scope": "weather", "rule_version": POLICY_VERSION})

    temp, wind, gust = (value(row, field) for field in CORE_FIELDS[:3])
    snow, visibility = value(row, "snowfall_cm"), value(row, "visibility_km")
    wind_level = wind_severity(wind, gust)
    if wind_level != "normal":
        red = wind_level == "critical"
        metrics = [field for field, number, threshold in
                   (("wind_speed_kmh", wind, WIND_LIMITS["wind_speed_kmh"][0]),
                    ("wind_gust_kmh", gust, WIND_LIMITS["wind_gust_kmh"][0]))
                   if number is not None and number >= threshold]
        add("wind", "باد شدید" if red else "باد و تندباد قابل‌توجه",
            "critical" if red else "change", metrics,
            "خطر ازدست‌دادن تعادل و دشواری حرکت" if red else "برای باد، پوشش و زمان ذخیره در نظر بگیرید")
        warnings[-1]["metric_severities"] = {
            field: "critical" if number >= red_threshold else "change"
            for field, number, red_threshold in
            (("wind_speed_kmh", wind, WIND_LIMITS["wind_speed_kmh"][1]),
             ("wind_gust_kmh", gust, WIND_LIMITS["wind_gust_kmh"][1]))
            if field in metrics
        }
    chill = wind_chill(temp, wind)
    if chill is not None and chill <= -10:
        add("cold", "سرمای شدید" if chill <= -28 else "سرمای ناشی از باد",
            "critical" if chill <= -28 else "change", ["temperature_c", "wind_chill_c"],
            "خطر آسیب به پوست بدون پوشش" if chill <= -28 else "پوشش گرم و محافظت در برابر باد لازم است")
    heat = heat_index(temp, value(row, "relative_humidity_pct"))
    if heat is not None and heat >= 32:
        add("heat", "گرمای خطرناک" if heat >= 40 else "فشار گرما",
            "critical" if heat >= 40 else "change", ["temperature_c", "relative_humidity_pct", "heat_index_c"],
            "فعالیت بدنی و آفتاب خطر گرمازدگی را افزایش می‌دهند")
    code = getattr(row, "weather_code", None)
    wmo = getattr(row, "wmo_code", None)
    if code == "thunder" or wmo in (95, 96, 99):
        add("lightning", "رعدوبرق", "critical", [], "خطر صاعقه در فضای باز؛ برنامه را تغییر دهید")
    if code in ("freezing-rain", "freezing-drizzle") and temp is not None and temp <= 0:
        add("freezing_rain", "بارش یخ‌زن", "critical", ["temperature_c", "precipitation_mm"],
            "احتمال تشکیل یخ و لغزندگی شدید")
    if visibility is not None and visibility <= .2:
        add("visibility", "دید بسیار کم", "change", ["visibility_km"], "جهت‌یابی دشوار می‌شود")
    if snow is not None and snow > 0 and wind is not None and wind >= 50 and visibility is not None and visibility <= .05:
        add("snow_wind_visibility", "برف، باد شدید و دید بسیار کم", "critical",
            ["snowfall_cm", "wind_speed_kmh", "visibility_km"], "خطر گم‌شدن و دشواری جدی حرکت")

    # Use real adjacent hourly readings: gaps do not count as persistence.
    by_at = _by_at if _by_at is not None else {item.forecast_at: item for item in records}
    if _by_at is None:
        by_at[row.forecast_at] = row
    def wet_cold(item):
        t, w, p = (value(item, f) for f in ("temperature_c", "wind_speed_kmh", "precipitation_mm"))
        return t is not None and w is not None and p is not None and t <= 10 and w >= 20 and p >= 1
    if wet_cold(row) and any(
        wet_cold(by_at[at]) for at in (row.forecast_at-timedelta(hours=1), row.forecast_at+timedelta(hours=1)) if at in by_at
    ):
        add("wet_cold", "بارش همراه سرما و باد", "change",
            ["temperature_c", "wind_speed_kmh", "precipitation_mm"], "خیس‌شدن و باد، اتلاف گرمای بدن را افزایش می‌دهند")
    window = [by_at.get(row.forecast_at-timedelta(hours=i)) for i in range(24)]
    # Total rain includes showers, but never interprets snowfall water as rain.
    def liquid(item):
        p, s = value(item, "precipitation_mm"), value(item, "snowfall_cm")
        return p if p is not None and s == 0 else None
    persistent = any(all(
        at in by_at and liquid(by_at[at]) is not None and liquid(by_at[at]) >= 5
        for at in (row.forecast_at + timedelta(hours=offset+i) for i in range(3))
    ) for offset in (-2, -1, 0))
    rain_total = sum(liquid(item) for item in window) if all(item is not None and liquid(item) is not None for item in window) else None
    snow_total = sum(value(item, "snowfall_cm") for item in window) if all(item is not None and value(item, "snowfall_cm") is not None for item in window) else None
    if persistent or (rain_total is not None and rain_total >= 40) or wmo in (65, 82):
        add("rain", "بارش سنگین یا مداوم", "change", ["precipitation_mm"], "پوشش ضدآب و بررسی عبور از آبراهه‌ها لازم است")
    if snow_total is not None and snow_total >= 15:
        add("snow", "برف تازهٔ قابل‌توجه", "change", ["snowfall_cm"], "حرکت و تشخیص مسیر دشوارتر می‌شود")
    missing = [field for field in CORE_FIELDS if value(row, field) is None]
    if wmo is None:
        missing.append("wmo_code")
    if value(row, "relative_humidity_pct") is None:
        missing.append("relative_humidity_pct")
    return {"warnings": warnings, "severity": max((w["severity"] for w in warnings), key=RANK.get, default="normal"),
            "wind_chill_c": round(chill, 1) if chill is not None else None,
            "heat_index_c": round(heat, 1) if heat is not None else None,
            "data_quality": "partial" if missing else "complete", "missing_inputs": sorted(set(missing)),
            "policy_version": POLICY_VERSION}


def assessment(row):
    cached = getattr(row, "_weather_assessment", None)
    return cached if cached is not None else assess(row)


def assess_records(records):
    by_at = {row.forecast_at: row for row in records}
    for row in records:
        row._weather_assessment = assess(row, _by_at=by_at)
    return records


def warning_intervals(records, *, now=None):
    intervals = []
    active = {}
    for row in sorted(records, key=lambda r: r.forecast_at):
        if now is not None and row.valid_to <= now:
            continue
        for warning in assessment(row)["warnings"]:
            key = warning["code"], warning["severity"]
            previous = active.get(key)
            if previous is not None and previous["end_at"] == warning["start_at"]:
                previous["end_at"] = warning["end_at"]
            else:
                previous = dict(warning)
                active[key] = previous
                intervals.append(previous)
    return sorted(intervals, key=lambda w: (-RANK[w["severity"]], w["start_at"]))


def representative_record(records):
    if not records:
        return None
    counts = Counter(row.weather_code for row in records)
    return max(records, key=lambda row: counts[row.weather_code])

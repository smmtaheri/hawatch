from __future__ import annotations

from datetime import date, datetime, timedelta

from django.conf import settings
from rest_framework.exceptions import NotFound

from hawatch.common.time import (
    ARRIVAL_FORECAST_TOLERANCE_MINUTES,
    PERIODS,
    SPEED_TIME_FACTORS,
    arrival_forecast_at,
    current_period_start_minutes,
    datetime_flags,
    day_payload,
    day_window,
    format_clock,
    format_duration,
    format_hhmm,
    localize_dt,
    now_tehran,
    paced_duration_minutes,
    period_hour_slots,
    period_window,
    planner_period_payload,
    to_fa_digits,
    timezone,
)
from hawatch.integrations.weather.demo import wind_compass
from hawatch.integrations.weather.ingest import latest_snapshot, snapshot_freshness
from hawatch.modules.catalog.seed import refresh_if_bucket_changed
from hawatch.modules.catalog.search import normalize_search_text
from hawatch.modules.forecasts.models import DemoSeedState, ForecastRecord, WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint


def _live_meta_parts() -> dict:
    snapshot = latest_snapshot()
    freshness = snapshot_freshness(snapshot)
    if snapshot is None:
        return {
            "data_mode": "live",
            "provider": "open-meteo",
            "source": "open-meteo-forecast",
            "seed_version": getattr(settings, "DEMO_SEED_VERSION", "hawatch-demo-v1"),
            "freshness": freshness,
            "generated_at": now_tehran().isoformat(),
            "last_generated_time": None,
        }
    return {
        "data_mode": "live",
        "provider": snapshot.provider,
        "source": snapshot.source,
        "seed_version": snapshot.catalog_version or "open-meteo-live",
        "freshness": freshness,
        "generated_at": _tehran_iso(snapshot.generated_at),
        "last_generated_time": _tehran_iso(snapshot.generated_at),
        "forecast_validity": {
            "valid_from": _tehran_iso(snapshot.valid_from),
            "valid_to": _tehran_iso(snapshot.valid_to),
        },
    }


def _tehran_iso(value: datetime | None) -> str | None:
    """Serialize public timestamps in Hawatch's fixed product timezone."""
    return now_tehran(value).isoformat() if value is not None else None


def meta_base(*, selected_date: date, period: str, extra: dict | None = None) -> dict:
    local = now_tehran()
    if settings.DEMO_DATA_ENABLED:
        state = DemoSeedState.objects.filter(key="demo").first()
        freshness = "ready"
        if state and state.last_hour_bucket != local.strftime("%Y-%m-%dT%H"):
            freshness = "stale"
        payload = {
            "schema_version": settings.HAWATCH_SCHEMA_VERSION,
            "timezone": str(timezone()),
            "current_local_time": local.isoformat(),
            "current_local_hour": local.hour,
            "selected_date": selected_date.isoformat(),
            "selected_period": period,
            "data_mode": "demo",
            "provider": "demo",
            "source": "hawatch-demo",
            "seed_version": settings.DEMO_SEED_VERSION,
            "freshness": freshness,
            "generated_at": _tehran_iso(state.generated_at) if state else local.isoformat(),
            "last_generated_time": _tehran_iso(state.generated_at) if state else None,
            "forecast_validity": {
                "valid_from": localize_dt(selected_date, 0).isoformat(),
                "valid_to": localize_dt(selected_date + timedelta(days=1), 0).isoformat(),
            },
        }
    else:
        live = _live_meta_parts()
        payload = {
            "schema_version": settings.HAWATCH_SCHEMA_VERSION,
            "timezone": str(timezone()),
            "current_local_time": local.isoformat(),
            "current_local_hour": local.hour,
            "selected_date": selected_date.isoformat(),
            "selected_period": period,
            **live,
        }
        if "forecast_validity" not in payload:
            payload["forecast_validity"] = {
                "valid_from": localize_dt(selected_date, 0).isoformat(),
                "valid_to": localize_dt(selected_date + timedelta(days=1), 0).isoformat(),
            }
    if extra:
        payload.update(extra)
    return payload


def weather_point_is_active(point: WeatherPoint) -> bool:
    """A point is public when active and linked to at least one active route."""
    return bool(
        point.is_active
        and (point.seo_indexable or RoutePoint.objects.filter(weather_point=point, route__is_active=True).exists())
    )


def serialize_point_profile(point: WeatherPoint, *, include_routes: bool = False) -> dict:
    elevation = point.elevation_m
    latitude = point.location.y if point.location else None
    longitude = point.location.x if point.location else None
    data = {
        "slug": point.slug,
        "tile_name": point.tile_name or point.short_label or point.name,
        "name": point.page_name or point.name,
        "short_category": point.short_category,
        "category": point.category,
        "category_key": point.category_key,
        "region": point.region,
        "elevation_m": elevation,
        "elevation_label": f"{to_fa_digits(elevation)} متر" if elevation is not None else "ارتفاع نامشخص",
        "latitude": latitude,
        "longitude": longitude,
        "image": point.image,
        "image_alt": point.image_alt,
        "href": f"/points/{point.slug}",
        "is_popular": point.is_popular,
        "popular_order": point.popular_order,
        "seo_indexable": point.seo_indexable,
        "data_mode": point.data_mode,
        "weather_point_slug": point.slug,
    }
    if include_routes:
        data["routes"] = [
            serialize_route_summary(route)
            for route in Route.objects.filter(
                points__weather_point=point,
                is_active=True,
            ).distinct().order_by("sort_order", "slug")
        ]
    return data


def serialize_route_summary(route: Route) -> dict:
    distance_km = float(route.distance_km) if route.distance_km is not None else None
    ascent_m = route.ascent_m
    timing_pending = not route_has_usable_timing(route)
    return {
        "slug": route.slug,
        "title": route.title,
        "trail_label": route.trail_label,
        "origin": route.origin,
        "target_label": route.target_label,
        "distance_km": distance_km,
        "distance_label": f"{to_fa_digits(distance_km)} km" if distance_km is not None else "—",
        "ascent_m": ascent_m,
        "ascent_label": f"{to_fa_digits(ascent_m)} m" if ascent_m is not None else "—",
        "featured": route.featured,
        "href": f"/routes/{route.slug}",
        "timing_status": route.timing_status,
        "timing_pending": timing_pending,
    }


def serialize_route(route: Route) -> dict:
    points = list(route.points.select_related("weather_point").all())
    siblings = [
        serialize_route_summary(item)
        for item in Route.objects.filter(
            is_active=True,
            target_weather_point=route.target_weather_point,
        )
        .exclude(pk=route.pk)
        .order_by("sort_order", "slug")
    ]
    distance_km = float(route.distance_km) if route.distance_km is not None else None
    timing_pending = not route_has_usable_timing(route, points)
    return {
        "slug": route.slug,
        "title": route.title,
        "subtitle": route.subtitle,
        "trail_label": route.trail_label,
        "origin": route.origin,
        "target_label": route.target_label,
        "region": route.region,
        "distance_km": distance_km,
        "distance_label": f"{to_fa_digits(distance_km)} km" if distance_km is not None else "—",
        "ascent_m": route.ascent_m,
        "ascent_label": f"{to_fa_digits(route.ascent_m)} m" if route.ascent_m is not None else "—",
        "round_trip_minutes": route.round_trip_minutes,
        "one_way_minutes": route.one_way_minutes,
        "default_start_minutes": route.default_start_minutes if route.default_start_minutes is not None else 360,
        "timing_status": route.timing_status,
        "timing_pending": timing_pending,
        "timing_method": route.timing_method or "",
        "timing_version": route.timing_version or "",
        "timing_confidence": route.timing_confidence or "",
        "timing_uncertainty_minutes": route.timing_uncertainty_minutes,
        "timing_source_urls": list(route.timing_source_urls or []),
        "featured": route.featured,
        "href": f"/routes/{route.slug}",
        "target_point": serialize_point_profile(route.target_weather_point) if route.target_weather_point else None,
        "points": [serialize_point(point) for point in points],
        "siblings": siblings,
    }


def weather_point_canonical_href(point: WeatherPoint) -> str:
    """Return the canonical public URL for a point."""
    return f"/points/{point.slug}"


def place_hero_assets(weather_point: WeatherPoint) -> tuple[str, str]:
    """Return the point's curated hero image, if any."""
    return (weather_point.image, weather_point.image_alt or weather_point.name) if weather_point.image else ("", "سطح پیش‌فرض پیش‌بینی")


def serialize_place_subject(
    weather_point: WeatherPoint,
    *,
    kind: str,
    display_name: str | None = None,
    context_label: str | None = None,
    elevation_m: int | None = None,
    aliases: list | None = None,
) -> dict:
    hero_image, hero_alt = place_hero_assets(weather_point)
    elev = elevation_m if elevation_m is not None else weather_point.elevation_m
    name = display_name or weather_point.name
    slug = weather_point.slug
    region = weather_point.region
    category = weather_point.category
    default_context = weather_point.region
    return {
        "kind": kind,
        "slug": slug,
        "weather_point_slug": weather_point.slug,
        "canonical_href": weather_point_canonical_href(weather_point),
        "name": name,
        "page_name": weather_point.page_name or name,
        "short_label": weather_point.short_label or name,
        "place_type": weather_point.place_type or "landmark",
        "identity_summary": weather_point.identity_summary or "",
        "importance": weather_point.importance or "support",
        "name_status": weather_point.name_status or "descriptive",
        "source_urls": list(weather_point.source_urls or []),
        "aliases": aliases if aliases is not None else (weather_point.aliases or []),
        "elevation_m": elev,
        "elevation_label": f"{to_fa_digits(elev)} متر" if elev is not None else "ارتفاع نامشخص",
        "latitude": weather_point.location.y,
        "longitude": weather_point.location.x,
        "context_label": context_label or default_context,
        "hero_image": hero_image,
        "hero_image_alt": hero_alt,
        "region": region,
        "category": category,
    }


def build_place_forecast(
    weather_point: WeatherPoint,
    *,
    selected_date: date,
    period: str,
    kind: str,
    related_routes: list[dict],
    subject_overrides: dict | None = None,
    climate: str | None = None,
    elevation_for_metrics: int | None = None,
) -> dict:
    """Shared forecast contract for point URLs."""
    refresh_if_bucket_changed()
    local = now_tehran()
    today = local.date()
    climate_key = climate or weather_point.climate or "alpine"
    elev_ref = elevation_for_metrics
    if elev_ref is None:
        elev_ref = weather_point.elevation_m
    subject = serialize_place_subject(
        weather_point,
        kind=kind,
    )
    if subject_overrides:
        subject.update(subject_overrides)

    records = _records_for_day(weather_point, selected_date)
    hourly = _hourly_for_period(weather_point, selected_date, period, now=local)
    current_payload = _reading_for_period_summary(weather_point, selected_date, period, local)

    place_name = subject["name"]
    short_name = weather_point.tile_name or weather_point.short_label or place_name
    period_payload = planner_period_payload(period)

    change = next(
        (
            item
            for item in records
            if item.severity in {"change", "critical"} and item.forecast_at.astimezone(timezone()).hour >= 11
        ),
        None,
    )
    critical = next((item for item in records if item.severity == "critical"), None)

    if current_payload and current_payload["is_current"]:
        hero_status = (
            f"{current_payload['icon']}　الان در {short_name}　"
            f"{current_payload.get('apparent_temperature_label', current_payload['temperature_label'])}　·　{current_payload['condition']}"
        )
    elif current_payload:
        hero_status = (
            f"{current_payload['icon']}　در {short_name}　"
            f"{current_payload.get('apparent_temperature_label', current_payload['temperature_label'])}　·　{current_payload['condition']}"
        )
    else:
        hero_status = "دادهٔ فعلی در دسترس نیست"
    if change:
        hour = change.forecast_at.astimezone(timezone()).hour
        hero_alert = f"!　تغییر مهم: از ساعت {to_fa_digits(hour)} {record_alert_label(change)}"
    else:
        hero_alert = "✓　شرایط فعلاً آرام‌تر است"

    morning_ok = (
        all(item.severity == "normal" for item in records if item.forecast_at.astimezone(timezone()).hour < 11)
        if records
        else True
    )
    if climate_key == "desert":
        decision_title = "حرکت پیش از تابش مستقیم، انتخاب بهتری است."
        decision_text = "در کویر، زمان برگشت و آب مهم‌تر از رسیدن سریع است؛ از ظهر گرما و باد شن‌زا بیشتر می‌شود."
    elif morning_ok:
        decision_title = "صبح برای شروع برنامه مناسب‌تر است."
        decision_text = "تا حدود ساعت ۱۱ شرایط آرام‌تر می‌ماند؛ بعد از آن باد در ارتفاعات بیشتر می‌شود."
        if critical:
            decision_text += f" از ساعت {to_fa_digits(critical.forecast_at.astimezone(timezone()).hour)} شرایط حساس‌تر می‌شود."
    else:
        decision_title = "برنامه را با احتیاط و زمان ذخیره بچین."
        decision_text = "تغییر شرایط زودتر از معمول شروع می‌شود؛ مسیر کوتاه‌تر یا شروع زودتر را در نظر بگیر."

    metrics: list[dict] = []
    if records:
        absolute_temperatures = [item.temperature_c for item in records]
        apparent_temperatures = [item.apparent_temperature_c for item in records]
        absolute_average = round(sum(absolute_temperatures) / len(absolute_temperatures))
        apparent_average = round(sum(apparent_temperatures) / len(apparent_temperatures))
        minimum_temperature = min(absolute_temperatures)
        maximum_temperature = max(absolute_temperatures)
        avg_wind = round(sum(item.wind_speed_kmh for item in records) / len(records))
        gust = max(item.wind_gust_kmh for item in records)
        vis = max(item.visibility_km for item in records)
        uv_values = [item.uv_index for item in records if item.uv_index is not None]
        uv = max(uv_values) if uv_values else None
        precip = max(item.precipitation_probability for item in records)
        rain_mm = sum(float(item.rain_mm) for item in records)
        snow_cm = sum(float(item.snowfall_cm or 0) for item in records)
        freeze = next((item.freezing_level_m for item in records if item.freezing_level_m), None)
        cloud_base = next((item.cloud_base_m for item in records if item.cloud_base_m), None)
        sunrise = format_clock(5, 22 if climate_key != "desert" else 24)
        sunset = format_clock(19, 46 if climate_key != "desert" else 38)
        metrics = [
            {
                "icon": "temperature",
                "label": "دمای حسی",
                "value": f"{to_fa_digits(apparent_average)}°",
                "note": "میانگین بازهٔ انتخابی",
                "color": "teal",
            },
            {
                "icon": "temperature",
                "label": "دمای مطلق",
                "value": f"{to_fa_digits(absolute_average)}°",
                "note": "دمای واقعی در ارتفاع نقطه",
                "color": "",
            },
            {
                "icon": "temperature",
                "label": "کمینهٔ دما",
                "value": f"{to_fa_digits(minimum_temperature)}°",
                "note": "در بازهٔ انتخابی",
                "color": "",
            },
            {
                "icon": "temperature",
                "label": "بیشینهٔ دما",
                "value": f"{to_fa_digits(maximum_temperature)}°",
                "note": "در بازهٔ انتخابی",
                "color": "",
            },
            {
                "icon": "precipitation",
                "label": "باران",
                "value": f"{_metric_number(rain_mm)} mm",
                "note": "مجموع بازهٔ انتخابی",
                "color": "amber" if rain_mm else "teal",
            },
            {
                "icon": "precipitation",
                "label": "برف",
                "value": f"{_metric_number(snow_cm)} cm",
                "note": "مجموع بازهٔ انتخابی",
                "color": "amber" if snow_cm else "teal",
            },
            {
                "icon": "wind-average",
                "label": "باد میانگین",
                "value": f"{to_fa_digits(avg_wind)} km/h",
                "note": wind_compass(records[0].wind_direction_deg),
                "color": "teal",
            },
            {
                "icon": "wind-gust",
                "label": "تندباد",
                "value": f"{to_fa_digits(gust)} km/h",
                "note": "بیشتر از ساعت ۱۱" if gust >= 20 else "آرام‌تر",
                "color": "coral" if gust >= 30 else "teal",
            },
            {
                "icon": "visibility",
                "label": "دید افقی",
                "value": f"+{to_fa_digits(int(vis))} km" if vis >= 10 else f"{to_fa_digits(vis)} km",
                "note": "کاهش دید در شرایط حساس",
                "color": "coral" if vis < 6 else "teal",
            },
            {
                "icon": "freezing-level",
                "label": "تراز صفر درجه",
                "value": f"{to_fa_digits(freeze)} m" if freeze is not None else "نامشخص",
                "note": (
                    "بالاتر از قله"
                    if freeze is not None and elev_ref is not None and freeze > elev_ref
                    else ("نزدیک سطح" if freeze is not None else "از provider دریافت نشده")
                ),
                "color": "",
            },
            {
                "icon": "cloud-base",
                "label": "پایهٔ ابر",
                "value": f"{to_fa_digits(cloud_base)} m" if cloud_base is not None else "نامشخص",
                "note": "نسبت به ارتفاع نقطه" if cloud_base is not None else "از provider دریافت نشده",
                "color": "",
            },
            {
                "icon": "uv-index",
                "label": "تابش فرابنفش",
                "value": _uv_label(uv),
                "note": "برای بخش‌های باز مسیر",
                "color": "amber" if (uv or 0) >= 6 else "teal",
            },
            {
                "icon": "precipitation",
                "label": "احتمال بارش",
                "value": f"{to_fa_digits(precip)}٪",
                "note": "بر اساس بازهٔ انتخابی",
                "color": "amber" if precip else "teal",
            },
            {
                "icon": "sunrise-sunset",
                "label": "طلوع / غروب",
                "value": f"{sunrise} / {sunset}",
                "note": "برای زمان‌بندی برگشت",
                "color": "",
            },
        ]

    days = []
    for day in day_window(today):
        payload = day_payload(day, today)
        days.append(payload)

    empty = not records and not hourly
    partial = bool(records) and not hourly
    meta = meta_base(selected_date=selected_date, period=period)
    if empty and not settings.DEMO_DATA_ENABLED:
        meta["freshness"] = "stale"
        hero_status = "دادهٔ زنده در دسترس نیست"
        hero_alert = "!　پیش‌بینی زنده هنوز ingest نشده است"
        decision_title = "دادهٔ زنده موجود نیست."
        decision_text = "تا زمان تکمیل ingestion، تصمیم قطعی از روی دادهٔ دمو ساخته نمی‌شود."

    decision = {
        "chip": f"{day_payload(selected_date, today)['label']} · جمع‌بندی هواچ",
        "title": decision_title,
        "text": decision_text,
    }
    hero = {"status": hero_status, "alert": hero_alert}
    routes_title = f"مسیرهای متصل به {short_name}"

    return {
        "subject": subject,
        "hero": hero,
        "forecast": {
            "days": days,
            "period": period_payload,
            "current": current_payload,
            "hourly": hourly,
            "meta": meta,
        },
        "metrics": metrics,
        "decision": decision,
        "related_routes": related_routes,
        "related_routes_title": routes_title,
        "alerts": [{"severity": "change", "title": hero_alert, "description": hero_alert}],
        "empty": empty,
        "partial": partial,
        # Temporary compatibility aliases for older consumers.
        "days": days,
        "period": period_payload,
        "current": current_payload,
        "weather": current_payload,
        "hourly": hourly,
        "meta": meta,
    }


def serialize_point(point: RoutePoint) -> dict:
    elevation = point.effective_elevation_m
    location = point.effective_location
    if point.weather_point_id:
        href = weather_point_canonical_href(point.weather_point)
    else:
        href = ""
    return {
        "slug": point.slug,
        "name": point.name,
        "elevation_m": elevation,
        "elevation_label": f"{to_fa_digits(elevation)} m" if elevation is not None else "ارتفاع نامشخص",
        "base_minutes": point.base_minutes,
        "cumulative_minutes": point.cumulative_minutes,
        "segment_minutes": point.segment_minutes,
        "segment_distance_m": point.segment_distance_m,
        "progress_pct": float(point.progress_pct) if point.progress_pct is not None else None,
        "timing_status": point.timing_status,
        "timing_pending": point.timing_status == RoutePoint.TimingStatus.PENDING,
        "sort_order": point.sort_order,
        "note": point.public_note,
        "axis_x": point.axis_x,
        "axis_y": point.axis_y,
        "href": href,
        "latitude": location.y if location else None,
        "longitude": location.x if location else None,
        "weather_point_slug": point.weather_point.slug if point.weather_point_id else None,
    }


def reading_payload(record: ForecastRecord, *, now: datetime | None = None) -> dict:
    local_at = record.forecast_at.astimezone(timezone())
    flags = datetime_flags(record.forecast_at, now)
    unavailable = []
    if record.cloud_cover_pct is None:
        unavailable.append("cloud_cover_pct")
    if record.uv_index is None:
        unavailable.append("uv_index")
    if record.freezing_level_m is None:
        unavailable.append("freezing_level_m")
    if record.cloud_base_m is None:
        unavailable.append("cloud_base_m")
    return {
        "time": format_clock(local_at.hour),
        "hour": local_at.hour,
        "forecast_at": _tehran_iso(record.forecast_at),
        "valid_from": _tehran_iso(record.valid_from),
        "valid_to": _tehran_iso(record.valid_to),
        "temperature_c": record.temperature_c,
        "temperature_label": f"{to_fa_digits(record.temperature_c)}°",
        "apparent_temperature_c": record.apparent_temperature_c,
        "apparent_temperature_label": f"{to_fa_digits(record.apparent_temperature_c)}°",
        "condition": record.condition_label,
        "icon": record.icon,
        "weather_code": record.weather_code,
        "wind_speed_kmh": record.wind_speed_kmh,
        "wind_label": f"باد {to_fa_digits(record.wind_speed_kmh)} km/h",
        "wind_gust_kmh": record.wind_gust_kmh,
        "wind_alert": wind_alert_payload(record),
        "wind_direction_deg": record.wind_direction_deg,
        "wind_direction_label": wind_compass(record.wind_direction_deg),
        "precipitation_probability": record.precipitation_probability,
        "precipitation_mm": float(record.precipitation_mm),
        "rain_mm": float(record.rain_mm),
        "snowfall_cm": float(record.snowfall_cm) if record.snowfall_cm is not None else None,
        "visibility_km": float(record.visibility_km),
        "cloud_cover_pct": record.cloud_cover_pct,
        "uv_index": record.uv_index,
        "freezing_level_m": record.freezing_level_m,
        "cloud_base_m": record.cloud_base_m,
        "fields_unavailable": unavailable,
        "severity": record.severity,
        "state": record.severity,
        "freshness": record.freshness,
        "provider": record.provider,
        "data_mode": record.data_mode,
        **flags,
    }


def wind_alert_payload(record: ForecastRecord) -> dict | None:
    """Expose strong wind separately from the sky/precipitation condition."""
    if record.wind_speed_kmh >= 30 or record.wind_gust_kmh >= 40:
        return {"code": "gale", "label": "تندباد", "severity": "critical"}
    if record.wind_speed_kmh >= 22:
        return {"code": "windy", "label": "بادخیز", "severity": "change"}
    return None


def record_alert_label(record: ForecastRecord) -> str:
    wind_alert = wind_alert_payload(record)
    if wind_alert:
        return f"{record.condition_label} · {wind_alert['label']}"
    return record.condition_label


def _uv_label(uv: int | None) -> str:
    if uv is None:
        return "نامشخص"
    if uv >= 8:
        level = "خیلی زیاد"
    elif uv >= 6:
        level = "زیاد"
    elif uv >= 3:
        level = "متوسط"
    else:
        level = "کم"
    return f"{to_fa_digits(uv)} · {level}"


def _metric_number(value: float) -> str:
    """Format a specialist metric without noisy trailing zeroes."""
    formatted = f"{value:.1f}".rstrip("0").rstrip(".")
    return to_fa_digits(formatted)


def _forecast_qs_for_point(point: WeatherPoint):
    qs = ForecastRecord.objects.filter(weather_point=point)
    if not settings.DEMO_DATA_ENABLED:
        return qs.filter(data_mode="live", provider="open-meteo")
    return qs


def _records_for_window(point: WeatherPoint, start: datetime, end: datetime) -> list[ForecastRecord]:
    return list(
        _forecast_qs_for_point(point)
        .filter(forecast_at__gte=start, forecast_at__lt=end)
        .order_by("forecast_at")
    )


def _records_for_day(point: WeatherPoint, selected_date: date) -> list[ForecastRecord]:
    start = localize_dt_safe(selected_date, 0)
    end = start + timedelta(days=1)
    return _records_for_window(point, start, end)


def _hourly_for_period(point: WeatherPoint, selected_date: date, period: str, *, now: datetime) -> list[dict]:
    window_start, window_end = period_window(selected_date, period)
    records = _records_for_window(point, window_start, window_end)
    by_at = {record.forecast_at.astimezone(timezone()).replace(minute=0, second=0, microsecond=0): record for record in records}
    slots = period_hour_slots(selected_date, period)
    hourly = []
    for index, (slot_date, hour) in enumerate(slots):
        slot_at = localize_dt_safe(slot_date, hour).replace(minute=0, second=0, microsecond=0)
        record = by_at.get(slot_at)
        if record is not None:
            if index + 1 < len(slots):
                next_slot_date, next_hour = slots[index + 1]
                slot_end = localize_dt_safe(next_slot_date, next_hour).replace(minute=0, second=0, microsecond=0)
            else:
                slot_end = window_end
            payload = reading_payload(record, now=now)
            payload.update(_display_slot_flags(slot_at, slot_end, now))
            hourly.append(payload)
    return hourly


def _display_slot_flags(slot_start: datetime, slot_end: datetime, now: datetime) -> dict:
    """Flag a rendered two-hour weather card by its displayed time window."""
    local_now = now_tehran(now)
    local_start = slot_start.astimezone(timezone())
    local_end = slot_end.astimezone(timezone())
    value_date = local_start.date()
    is_current = local_start <= local_now < local_end
    is_past = local_now >= local_end
    return {
        "is_yesterday": value_date == local_now.date() - timedelta(days=1),
        "is_today": value_date == local_now.date(),
        "is_past": is_past,
        "is_current": is_current,
        "is_future": not is_current and not is_past,
    }

def _reading_for_period_summary(
    point: WeatherPoint,
    selected_date: date,
    period: str,
    local: datetime,
) -> dict | None:
    """Return a reading strictly inside the selected period window, without whole-day fallback."""
    window_start, window_end = period_window(selected_date, period)
    period_records = _records_for_window(point, window_start, window_end)
    if not period_records:
        return None
    if window_start <= local < window_end:
        slots = period_hour_slots(selected_date, period)
        active_index = max(
            (index for index, (slot_date, hour) in enumerate(slots) if local >= localize_dt_safe(slot_date, hour)),
            default=0,
        )
        slot_date, slot_hour = slots[active_index]
        slot_start = localize_dt_safe(slot_date, slot_hour).replace(minute=0, second=0, microsecond=0)
        if active_index + 1 < len(slots):
            next_slot_date, next_hour = slots[active_index + 1]
            slot_end = localize_dt_safe(next_slot_date, next_hour).replace(minute=0, second=0, microsecond=0)
        else:
            slot_end = window_end
        record = next(
            (
                item
                for item in period_records
                if item.forecast_at.astimezone(timezone()).replace(minute=0, second=0, microsecond=0) == slot_start
            ),
            None,
        )
        if record is None:
            record = min(
                period_records,
                key=lambda item: abs((item.forecast_at.astimezone(timezone()) - slot_start).total_seconds()),
            )
        payload = reading_payload(record, now=local)
        payload.update(_display_slot_flags(slot_start, slot_end, local))
        return payload
        closest = min(
            period_records,
            key=lambda item: abs((item.forecast_at.astimezone(timezone()) - local).total_seconds()),
        )
        return reading_payload(closest, now=local)
    hourly = _hourly_for_period(point, selected_date, period, now=local)
    if hourly:
        return hourly[len(hourly) // 2]
    return None


def point_profile_forecast(point: WeatherPoint, *, selected_date: date, period: str) -> dict:
    routes = [
        serialize_route_summary(route)
        for route in Route.objects.filter(points__weather_point=point, is_active=True).distinct().order_by("sort_order", "slug")
    ]
    place = build_place_forecast(
        point,
        selected_date=selected_date,
        period=period,
        kind="point",
        related_routes=routes,
        climate=point.climate,
        elevation_for_metrics=point.elevation_m,
    )
    return {**place, "point": serialize_point_profile(point, include_routes=True), "updated_label": ""}


def localize_dt_safe(value: date, hour: int):
    from hawatch.common.time import localize_dt

    return localize_dt(value, hour)


def route_has_usable_timing(route: Route, points: list[RoutePoint] | None = None) -> bool:
    """True only for complete estimated/curated timing; never uses base_minutes."""
    from hawatch.modules.routes.timing import route_timing_complete

    ordered = points if points is not None else list(route.points.all())
    return route_timing_complete(
        timing_status=route.timing_status,
        one_way_minutes=route.one_way_minutes,
        points=ordered,
    )


def _point_arrival_minutes(point: RoutePoint, *, start_minutes: int, speed: str, timing_pending: bool) -> int | None:
    if timing_pending or point.timing_status == RoutePoint.TimingStatus.PENDING:
        return None
    # Estimated/curated arrivals require cumulative_minutes only — never invent from base_minutes.
    medium = point.cumulative_minutes
    if medium is None:
        return None
    return start_minutes + paced_duration_minutes(medium, speed)


def _closest_point_forecast(weather_point: WeatherPoint, target_at: datetime, *, now: datetime):
    """Select this point's own forecast closest to arrival within ±tolerance.

    Never substitutes another WeatherPoint (including the target point).
    Tie-break when distances are equal: earlier forecast_at, then lower primary key.
    Does not rely on queryset default ordering.
    """
    tolerance = timedelta(minutes=ARRIVAL_FORECAST_TOLERANCE_MINUTES)
    candidates = list(
        _forecast_qs_for_point(weather_point).filter(
            forecast_at__gte=target_at - tolerance,
            forecast_at__lte=target_at + tolerance,
        )
    )
    if not candidates:
        return None
    record = min(
        candidates,
        key=lambda row: (
            abs((row.forecast_at - target_at).total_seconds()),
            row.forecast_at,
            row.pk,
        ),
    )
    return reading_payload(record, now=now)


def route_forecast(route: Route, *, selected_date: date, period: str, start_minutes: int, speed: str) -> dict:
    refresh_if_bucket_changed()
    local = now_tehran()
    today = local.date()
    points = list(route.points.select_related("weather_point", "route").all())
    timing_pending = not route_has_usable_timing(route, points)
    planned = []
    for point in points:
        arrival = _point_arrival_minutes(point, start_minutes=start_minutes, speed=speed, timing_pending=timing_pending)
        wp = point.weather_point
        weather = None
        arrival_at = None
        point_timing_pending = (
            timing_pending
            or point.timing_status == RoutePoint.TimingStatus.PENDING
            or point.cumulative_minutes is None
        )
        # Arrival-based weather only when validated cumulative timing exists for THIS point's WeatherPoint.
        if wp and arrival is not None and not point_timing_pending:
            arrival_at = arrival_forecast_at(selected_date, arrival)
            weather = _closest_point_forecast(wp, arrival_at, now=local)
        else:
            weather = None
        weather_available = weather is not None
        # Point-card state comes only from the matched forecast severity — never from elapsed-time thresholds.
        arrival_state = weather["severity"] if weather else "normal"
        pending_note = "زمان‌بندی مسیر هنوز نهایی نشده"
        if point_timing_pending:
            condition = "زمان‌بندی در دسترس نیست"
            note = point.public_note or pending_note
        elif not weather_available:
            condition = "در دسترس نیست"
            note = point.public_note
        else:
            condition = weather["condition"]
            note = point.public_note
        planned.append(
            {
                **serialize_point(point),
                "arrival_minutes": arrival,
                "arrival_at": arrival_at.isoformat() if arrival_at is not None else None,
                "time": format_hhmm(arrival) if arrival is not None else "—",
                "timing_estimated": route.timing_status == Route.TimingStatus.ESTIMATED and not timing_pending,
                "timing_pending": point_timing_pending,
                "timing_confidence": route.timing_confidence or "",
                "timing_uncertainty_minutes": route.timing_uncertainty_minutes,
                "weather": weather,
                "weather_available": weather_available,
                "forecast_at": weather.get("forecast_at") if weather else None,
                # Route cards are user-facing weather summaries, so expose the
                # apparent temperature there too. Keep absolute temperature
                # available for specialist consumers and threshold logic.
                "temp": weather["apparent_temperature_c"] if weather else None,
                "temp_absolute": weather["temperature_c"] if weather else None,
                "wind": weather["wind_speed_kmh"] if weather else None,
                "icon": weather["icon"] if weather else "—",
                "condition": condition,
                "state": arrival_state if weather_available else "normal",
                "note": note,
            }
        )

    target_point = route.target_weather_point
    # Target-point hourly strip is independent of route-point severity.
    hourly = _hourly_for_period(target_point, selected_date, period, now=local) if target_point else []

    finish = planned[-1] if planned else None
    critical_point = next((item for item in planned if item["state"] == "critical"), finish)
    summary_state = "critical" if any(item["state"] == "critical" for item in planned) else "change" if any(item["state"] == "change" for item in planned) else "normal"
    state_label = {"critical": "هشدار", "change": "احتیاط", "normal": "حرکت مناسب"}[summary_state]

    def _point_time_phrase(point: dict | None) -> str | None:
        if not point or timing_pending:
            return None
        time_label = point.get("time")
        if not time_label or time_label == "—":
            return None
        return f"حدود {time_label}"

    def _status_phrase(label: str, point: dict, detail: str | None = None) -> str:
        parts = [f"{label}: {point['name']}"]
        if detail:
            parts.append(detail)
        return " · ".join(parts)

    if summary_state == "critical" and critical_point:
        time_phrase = _point_time_phrase(critical_point)
        if timing_pending:
            state_summary = f"در {critical_point['name']} شرایط پرریسک گزارش شده؛ زمان‌بندی مسیر هنوز نهایی نیست."
            hero_status = _status_phrase("نقطهٔ حساس", critical_point, "پیش‌بینی بازه‌ای")
        else:
            state_summary = f"در {time_phrase or 'مسیر'} شرایط پرریسک می‌شود؛ امکان برگشت را از قبل در برنامه نگه دار."
            hero_status = _status_phrase("نقطهٔ حساس", critical_point, time_phrase)
    elif summary_state == "change" and critical_point:
        time_phrase = _point_time_phrase(critical_point)
        if timing_pending:
            state_summary = f"از {critical_point['name']} تغییر شرایط محتمل است؛ زمان‌بندی مسیر هنوز نهایی نیست."
            hero_status = f"تغییر مهم: {critical_point['name']}"
        else:
            state_summary = f"از {time_phrase or critical_point['name']} تغییر شرایط شروع می‌شود؛ زمان برگشت و تجهیزات را جدی‌تر چک کن."
            hero_status = _status_phrase("تغییر مهم", critical_point, time_phrase)
    else:
        state_summary = "شرایط مسیر برای شروع آرام‌تر است؛ همچنان پیش‌بینی نقطه‌های بالاتر را دنبال کن."
        hero_status = "شرایط مسیر فعلاً آرام‌تر است"
        critical_point = finish

    gear = []

    def add_gear(*items: str) -> None:
        for item in items:
            if item not in gear:
                gear.append(item)

    # Keep equipment structured and language-independent. The prose below is
    # retained for API compatibility, while the UI renders only these stable
    # icon keys in the share card.
    add_gear("hiking-boots", "backpack", "water-bottle")
    if timing_pending:
        add_gear("first-aid", "power-bank")
    if route.one_way_minutes and route.one_way_minutes >= 360:
        add_gear("energy-snack", "headlamp")
    if summary_state == "critical":
        add_gear("compass", "whistle")
    if critical_point and (critical_point.get("wind") or 0) >= 25:
        add_gear("waterproof-shell", "trekking-poles")
    if critical_point and (critical_point.get("temp") is not None and critical_point["temp"] <= 2):
        add_gear("gloves", "insulated-jacket", "beanie")

    recommendations = []
    if timing_pending:
        recommendations.append("زمان‌بندی دقیق مسیر هنوز نهایی نشده؛ زمان رسیدن و مسافت تجمعی فعلاً در دسترس نیست.")
    elif route.timing_status == Route.TimingStatus.ESTIMATED:
        recommendations.append(
            "زمان‌ها تخمینی‌اند (بدون استراحت طولانی) و بسته به آمادگی، زمین و شرایط هوا تغییر می‌کنند."
        )
    if summary_state == "critical":
        recommendations.append("اگر رعدوبرق، باد شدید یا دید محدود فعال است، صعود را ادامه نده و زودتر برگرد.")
    if critical_point and (critical_point.get("wind") or 0) >= 25:
        recommendations.append("باد در بخش حساس بالاست؛ بندهای کوله و باتوم را محکم کن و روی یال توقف طولانی نداشته باش.")
    if critical_point and (critical_point.get("temp") is not None and critical_point["temp"] <= 2):
        recommendations.append("دستکش گرم، لایهٔ عایق و عینک محافظ همراه داشته باش؛ در ارتفاع توقف طولانی نکن.")
    if not recommendations:
        recommendations.append("یک لایهٔ اضافه، آب کافی و چراغ پیشانی همراه داشته باش؛ شرایط فعلاً آرام‌تر است.")

    start_label = format_hhmm(start_minutes)
    finish_label = finish["time"] if finish and finish["time"] != "—" else "—"
    if timing_pending:
        decision_title = f"با حرکت ساعت {start_label}، زمان رسیدن هنوز مشخص نیست."
        duration_label = "نامشخص"
        arrival_label = "—"
    else:
        duration = paced_duration_minutes(route.one_way_minutes, speed) if route.one_way_minutes else None
        duration_label = format_duration(duration) if duration is not None else "—"
        arrival_label = finish_label
        decision_title = f"با حرکت ساعت {start_label}، حدود {finish_label} به نقطه می‌رسی."

    days = [day_payload(day, today) for day in day_window(today)]
    stats = [
        {
            "label": "مسافت",
            "value": f"{to_fa_digits(route.distance_km)} km" if route.distance_km is not None else "نامشخص",
        },
        {
            "label": "صعود",
            "value": f"{to_fa_digits(route.ascent_m)} m" if route.ascent_m is not None else "نامشخص",
        },
        {"label": "زمان تخمینی مسیر", "value": duration_label},
        {"label": "رسیدن به نقطه", "value": arrival_label},
    ]
    return {
        "route": serialize_route(route),
        "days": days,
        "period": planner_period_payload(period),
        "start_minutes": start_minutes,
        "start_time": start_label,
        "speed": speed,
        "speed_options": list(SPEED_TIME_FACTORS.keys()),
        "timing_pending": timing_pending,
        "timing_status": route.timing_status,
        "timing_confidence": route.timing_confidence or "",
        "timing_uncertainty_minutes": route.timing_uncertainty_minutes,
        "timing_version": route.timing_version or "",
        "points": planned,
        "hourly": hourly,
        "hero": {"status": hero_status},
        "stats": stats,
        "decision": {
            "chip": f"پیش‌بینی مسیر · {day_payload(selected_date, today)['label']}",
            "title": decision_title,
            "status": state_label,
            "state": summary_state,
            "summary": state_summary,
            "hero_status": hero_status,
            "critical_name": critical_point["name"] if critical_point else "",
            "critical_time": critical_point["time"] if critical_point else "",
            "critical_note": critical_point["note"] if critical_point else "",
            "recommendations": recommendations[:3],
            "gear": gear[:8],
            "start": start_label,
            "finish": finish_label,
            "speed": speed,
            "timing_pending": timing_pending,
        },
        "empty": not planned,
        "meta": meta_base(
            selected_date=selected_date,
            period=period,
            extra={
                "selected_start_time": start_label,
                "selected_speed": speed,
                "timing_pending": timing_pending,
                "timing_status": route.timing_status,
                "timing_version": route.timing_version or "",
            },
        ),
    }


def list_points(*, query: str = "") -> list[WeatherPoint]:
    qs = WeatherPoint.objects.filter(is_active=True).order_by("-is_popular", "popular_order", "slug")
    if query:
        normalized = normalize_search_text(query)
        qs = [
            item
            for item in qs
            if any(
                normalized in normalize_search_text(str(value))
                for value in (
                    item.page_name or item.name,
                    item.tile_name,
                    item.short_category,
                    item.category,
                    *(item.aliases or []),
                )
            )
        ]
        return qs[:6]
    return list(qs.filter(is_popular=True)[:4])


def get_point(slug: str) -> WeatherPoint:
    try:
        point = WeatherPoint.objects.get(slug=slug, is_active=True)
    except WeatherPoint.DoesNotExist as exc:
        raise NotFound({"detail": "نقطه پیدا نشد."}) from exc
    if not weather_point_is_active(point):
        raise NotFound({"detail": "نقطه پیدا نشد."})
    return point


def get_weather_point(slug: str) -> WeatherPoint:
    try:
        point = WeatherPoint.objects.get(slug=slug)
    except WeatherPoint.DoesNotExist as exc:
        raise NotFound({"detail": "نقطهٔ هواشناسی پیدا نشد."}) from exc
    if slug.startswith(("dest:", "route:")):
        raise NotFound({"detail": "نقطه پیدا نشد."}) from None
    if not weather_point_is_active(point):
        raise NotFound({"detail": "نقطهٔ هواشناسی پیدا نشد."}) from None
    return point


def serialize_weather_point(point: WeatherPoint) -> dict:
    return {
        "slug": point.slug,
        "name": point.name,
        "page_name": point.page_name or point.name,
        "short_label": point.short_label or point.name,
        "place_type": point.place_type or "landmark",
        "identity_summary": point.identity_summary or "",
        "importance": point.importance or "support",
        "name_status": point.name_status or "descriptive",
        "source_urls": list(point.source_urls or []),
        "aliases": point.aliases or [],
        "kind": point.kind,
        "elevation_m": point.elevation_m,
        "elevation_label": f"{to_fa_digits(point.elevation_m)} m" if point.elevation_m is not None else "ارتفاع نامشخص",
        "latitude": point.location.y,
        "longitude": point.location.x,
        "status": point.status,
        "provenance": point.provenance,
        "href": weather_point_canonical_href(point),
        "canonical_href": weather_point_canonical_href(point),
        "tile_name": point.tile_name or point.short_label or point.name,
        "category": point.category,
        "category_key": point.category_key,
        "region": point.region,
        "image": point.image,
        "image_alt": point.image_alt,
        "seo_indexable": point.seo_indexable,
    }


def related_routes_for_weather_point(point: WeatherPoint) -> list[dict]:
    routes = (
        Route.objects.filter(
            points__weather_point=point,
            is_active=True,
        )
        .distinct()
        .order_by("sort_order", "slug")
    )
    return [serialize_route_summary(route) for route in routes]


def point_forecast(weather_point: WeatherPoint, *, selected_date: date, period: str) -> dict:
    routes = related_routes_for_weather_point(weather_point)
    place = build_place_forecast(
        weather_point,
        selected_date=selected_date,
        period=period,
        kind="point",
        related_routes=routes,
    )
    return {
        **place,
        "point": {
            **serialize_weather_point(weather_point),
            "canonical_href": place["subject"]["canonical_href"],
        },
        "related_routes": routes,
        "updated_label": "",
    }


def get_route(slug: str) -> Route:
    try:
        route = Route.objects.select_related("origin_weather_point", "target_weather_point").get(slug=slug, is_active=True)
    except Route.DoesNotExist as exc:
        raise NotFound({"detail": "مسیر پیدا نشد."}) from exc
    return route

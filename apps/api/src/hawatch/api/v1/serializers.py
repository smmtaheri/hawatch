from __future__ import annotations

from datetime import date, datetime, timedelta

from django.conf import settings
from rest_framework.exceptions import NotFound

from hawatch.common.time import (
    PERIODS,
    SPEED_MULTIPLIERS,
    arrival_forecast_at,
    datetime_flags,
    day_payload,
    day_window,
    format_clock,
    format_duration,
    format_hhmm,
    now_tehran,
    period_hour_slots,
    period_window,
    to_fa_digits,
    timezone,
)
from hawatch.integrations.weather.demo import wind_compass
from hawatch.integrations.weather.ingest import latest_snapshot, snapshot_freshness
from hawatch.modules.catalog.seed import refresh_if_bucket_changed
from hawatch.modules.destinations.models import Destination
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
        "generated_at": snapshot.generated_at.isoformat(),
        "last_generated_time": snapshot.generated_at.isoformat(),
        "forecast_validity": {
            "valid_from": snapshot.valid_from.isoformat() if snapshot.valid_from else None,
            "valid_to": snapshot.valid_to.isoformat() if snapshot.valid_to else None,
        },
    }


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
            "generated_at": state.generated_at.isoformat() if state else local.isoformat(),
            "last_generated_time": state.generated_at.isoformat() if state else None,
            "forecast_validity": {
                "valid_from": (selected_date.isoformat() + "T00:00:00"),
                "valid_to": ((selected_date + timedelta(days=1)).isoformat() + "T00:00:00"),
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
                "valid_from": (selected_date.isoformat() + "T00:00:00"),
                "valid_to": ((selected_date + timedelta(days=1)).isoformat() + "T00:00:00"),
            }
    if extra:
        payload.update(extra)
    return payload


def destination_weather_point(destination: Destination) -> WeatherPoint | None:
    point = (
        WeatherPoint.objects.filter(destination=destination, kind=WeatherPoint.Kind.DESTINATION)
        .exclude(slug__startswith="dest:")
        .order_by("id")
        .first()
    )
    if point:
        return point
    return WeatherPoint.objects.filter(slug=f"dest:{destination.slug}").first()


def serialize_destination(destination: Destination, *, include_routes: bool = False) -> dict:
    data = {
        "slug": destination.slug,
        "tile_name": destination.tile_name,
        "name": destination.name,
        "short_category": destination.short_category,
        "category": destination.category,
        "category_key": destination.category_key,
        "region": destination.region,
        "elevation_m": destination.elevation_m,
        "elevation_label": f"{to_fa_digits(destination.elevation_m)} متر",
        "latitude": destination.location.y,
        "longitude": destination.location.x,
        "image": destination.image,
        "image_alt": destination.image_alt,
        "href": f"/destination/{destination.slug}",
        "is_popular": destination.is_popular,
        "popular_order": destination.popular_order,
        "data_mode": destination.data_mode,
    }
    if include_routes:
        data["routes"] = [serialize_route_summary(route) for route in destination.routes.all().order_by("sort_order")]
    return data


def serialize_route_summary(route: Route) -> dict:
    distance_km = float(route.distance_km) if route.distance_km is not None else None
    ascent_m = route.ascent_m
    return {
        "slug": route.slug,
        "title": route.title,
        "trail_label": route.trail_label,
        "origin": route.origin,
        "destination_label": route.destination_label,
        "distance_km": distance_km,
        "distance_label": f"{to_fa_digits(distance_km)} km" if distance_km is not None else "—",
        "ascent_m": ascent_m,
        "ascent_label": f"{to_fa_digits(ascent_m)} m" if ascent_m is not None else "—",
        "featured": route.featured,
        "href": f"/routes/{route.slug}",
        "timing_status": route.timing_status,
        "timing_pending": route.timing_status == Route.TimingStatus.PENDING,
    }


def serialize_route(route: Route) -> dict:
    points = list(route.points.select_related("destination", "weather_point").all())
    siblings = [
        serialize_route_summary(item)
        for item in Route.objects.filter(destination=route.destination).exclude(pk=route.pk).order_by("sort_order")
    ]
    distance_km = float(route.distance_km) if route.distance_km is not None else None
    return {
        "slug": route.slug,
        "title": route.title,
        "subtitle": route.subtitle,
        "trail_label": route.trail_label,
        "origin": route.origin,
        "destination_label": route.destination_label,
        "region": route.region,
        "distance_km": distance_km,
        "distance_label": f"{to_fa_digits(distance_km)} km" if distance_km is not None else "—",
        "ascent_m": route.ascent_m,
        "ascent_label": f"{to_fa_digits(route.ascent_m)} m" if route.ascent_m is not None else "—",
        "round_trip_minutes": route.round_trip_minutes,
        "default_start_minutes": route.default_start_minutes if route.default_start_minutes is not None else 360,
        "timing_status": route.timing_status,
        "timing_pending": route.timing_status == Route.TimingStatus.PENDING,
        "featured": route.featured,
        "href": f"/routes/{route.slug}",
        "parent": serialize_destination(route.destination),
        "points": [serialize_point(point) for point in points],
        "siblings": siblings,
    }


def serialize_point(point: RoutePoint) -> dict:
    elevation = point.effective_elevation_m
    location = point.effective_location
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
        "note": point.note,
        "axis_x": point.axis_x,
        "axis_y": point.axis_y,
        "href": f"/routes/{point.route.slug}/points/{point.slug}",
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
        "forecast_at": record.forecast_at.isoformat(),
        "valid_from": record.valid_from.isoformat(),
        "valid_to": record.valid_to.isoformat(),
        "temperature_c": record.temperature_c,
        "temperature_label": f"{to_fa_digits(record.temperature_c)}°",
        "apparent_temperature_c": record.apparent_temperature_c,
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
    hourly = []
    for slot_date, hour in period_hour_slots(selected_date, period):
        slot_at = localize_dt_safe(slot_date, hour).replace(minute=0, second=0, microsecond=0)
        record = by_at.get(slot_at)
        if record is not None:
            hourly.append(reading_payload(record, now=now))
    return hourly

def destination_forecast(destination: Destination, *, selected_date: date, period: str) -> dict:
    refresh_if_bucket_changed()
    local = now_tehran()
    today = local.date()
    point = destination_weather_point(destination)
    if point is None:
        raise NotFound({"detail": "نقطهٔ هوای مقصد پیدا نشد."})
    records = _records_for_day(point, selected_date)
    hourly = _hourly_for_period(point, selected_date, period, now=local)

    now_record = min(records, key=lambda item: abs(item.forecast_at.astimezone(timezone()).hour - local.hour), default=None) if records else None
    if selected_date != today:
        now_record = records[len(records) // 2] if records else None

    change = next((item for item in records if item.severity in {"change", "critical"} and item.forecast_at.astimezone(timezone()).hour >= 12), None)
    critical = next((item for item in records if item.severity == "critical"), None)

    if now_record:
        hero_status = f"{now_record.icon}　الان در {destination.tile_name}　{to_fa_digits(now_record.temperature_c)}°　·　{now_record.condition_label}"
    else:
        hero_status = "دادهٔ فعلی در دسترس نیست"
    if change:
        hour = change.forecast_at.astimezone(timezone()).hour
        hero_alert = f"!　تغییر مهم: از ساعت {to_fa_digits(hour)} {record_alert_label(change)}"
    else:
        hero_alert = "✓　شرایط فعلاً آرام‌تر است"

    morning_ok = all(item.severity == "normal" for item in records if item.forecast_at.astimezone(timezone()).hour < 12) if records else True
    if destination.climate == "desert":
        decision_title = "حرکت پیش از تابش مستقیم، انتخاب بهتری است."
        decision_text = "در کویر، زمان برگشت و آب مهم‌تر از رسیدن سریع است؛ از ظهر گرما و باد شن‌زا بیشتر می‌شود."
    elif morning_ok:
        decision_title = "صبح برای شروع برنامه مناسب‌تر است."
        decision_text = "تا حدود ساعت ۱۰ شرایط آرام‌تر می‌ماند؛ بعد از آن باد در ارتفاعات بیشتر می‌شود."
        if critical:
            decision_text += f" از ساعت {to_fa_digits(critical.forecast_at.astimezone(timezone()).hour)} شرایط حساس‌تر می‌شود."
    else:
        decision_title = "برنامه را با احتیاط و زمان ذخیره بچین."
        decision_text = "تغییر شرایط زودتر از معمول شروع می‌شود؛ مسیر کوتاه‌تر یا شروع زودتر را در نظر بگیر."

    metrics = []
    if records:
        avg_wind = round(sum(item.wind_speed_kmh for item in records) / len(records))
        gust = max(item.wind_gust_kmh for item in records)
        vis = max(item.visibility_km for item in records)
        uv_values = [item.uv_index for item in records if item.uv_index is not None]
        uv = max(uv_values) if uv_values else None
        precip = max(item.precipitation_probability for item in records)
        freeze = next((item.freezing_level_m for item in records if item.freezing_level_m), None)
        cloud_base = next((item.cloud_base_m for item in records if item.cloud_base_m), None)
        sunrise = format_clock(5, 22 if destination.climate != "desert" else 24)
        sunset = format_clock(19, 46 if destination.climate != "desert" else 38)
        metrics = [
            {"icon": "⌁", "label": "باد میانگین", "value": f"{to_fa_digits(avg_wind)} km/h", "note": wind_compass(records[0].wind_direction_deg), "color": "teal"},
            {"icon": "↯", "label": "تندباد", "value": f"{to_fa_digits(gust)} km/h", "note": "بیشتر از ساعت ۱۲" if gust >= 20 else "آرام‌تر", "color": "coral" if gust >= 30 else "teal"},
            {"icon": "◌", "label": "دید افقی", "value": f"+{to_fa_digits(int(vis))} km" if vis >= 10 else f"{to_fa_digits(vis)} km", "note": "کاهش دید در شرایط حساس", "color": "coral" if vis < 6 else "teal"},
            {
                "icon": "❄",
                "label": "تراز صفر درجه",
                "value": f"{to_fa_digits(freeze)} m" if freeze is not None else "نامشخص",
                "note": "بالاتر از قله" if freeze is not None and freeze > destination.elevation_m else ("نزدیک سطح" if freeze is not None else "از provider دریافت نشده"),
                "color": "",
            },
            {
                "icon": "☁",
                "label": "پایهٔ ابر",
                "value": f"{to_fa_digits(cloud_base)} m" if cloud_base is not None else "نامشخص",
                "note": "نسبت به ارتفاع مقصد" if cloud_base is not None else "از provider دریافت نشده",
                "color": "",
            },
            {"icon": "☀", "label": "تابش فرابنفش", "value": _uv_label(uv), "note": "برای بخش‌های باز مسیر", "color": "amber" if (uv or 0) >= 6 else "teal"},
            {"icon": "☂", "label": "بارش", "value": f"{to_fa_digits(precip)}٪", "note": "بر اساس بازهٔ انتخابی", "color": "amber" if precip else "teal"},
            {"icon": "◷", "label": "طلوع / غروب", "value": f"{sunrise} / {sunset}", "note": "برای زمان‌بندی برگشت", "color": ""},
        ]

    days = [day_payload(day, today) for day in day_window(today)]
    empty = not records
    meta = meta_base(selected_date=selected_date, period=period)
    if empty and not settings.DEMO_DATA_ENABLED:
        meta["freshness"] = "stale"
        hero_status = "دادهٔ زنده در دسترس نیست"
        hero_alert = "!　پیش‌بینی زنده هنوز ingest نشده است"
        decision_title = "دادهٔ زنده موجود نیست."
        decision_text = "تا زمان تکمیل ingestion، تصمیم قطعی از روی دادهٔ دمو ساخته نمی‌شود."
    updated_label = f"آخرین به‌روزرسانی: امروز، {format_clock(local.hour, local.minute)}"
    if meta.get("last_generated_time"):
        generated = meta["last_generated_time"]
        updated_label = f"آخرین به‌روزرسانی: {generated}"
    elif empty and not settings.DEMO_DATA_ENABLED:
        updated_label = "آخرین به‌روزرسانی: نامشخص"
    return {
        "destination": serialize_destination(destination, include_routes=True),
        "days": days,
        "period": PERIODS[period],
        "current": reading_payload(now_record, now=local) if now_record else None,
        "hourly": hourly,
        "metrics": metrics,
        "alerts": [
            {"severity": "change", "title": hero_alert, "description": hero_alert},
        ],
        "hero": {"status": hero_status, "alert": hero_alert},
        "decision": {
            "chip": f"{day_payload(selected_date, today)['label']} · جمع‌بندی هواچ",
            "title": decision_title,
            "text": decision_text,
        },
        "updated_label": updated_label,
        "empty": empty,
        "meta": meta,
    }


def localize_dt_safe(value: date, hour: int):
    from hawatch.common.time import localize_dt

    return localize_dt(value, hour)


def _point_arrival_minutes(point: RoutePoint, *, start_minutes: int, multiplier: float, timing_pending: bool) -> int | None:
    if timing_pending:
        return None
    minutes = point.cumulative_minutes
    if minutes is None:
        minutes = point.base_minutes
    if minutes is None:
        return None
    return start_minutes + round(minutes * multiplier)


def route_forecast(route: Route, *, selected_date: date, period: str, start_minutes: int, speed: str) -> dict:
    refresh_if_bucket_changed()
    local = now_tehran()
    today = local.date()
    multiplier = SPEED_MULTIPLIERS[speed]
    timing_pending = route.timing_status == Route.TimingStatus.PENDING
    points = list(route.points.select_related("weather_point", "route").all())
    planned = []
    for point in points:
        arrival = _point_arrival_minutes(point, start_minutes=start_minutes, multiplier=multiplier, timing_pending=timing_pending)
        wp = point.weather_point
        record = None
        if wp and arrival is not None:
            target_at = arrival_forecast_at(selected_date, arrival)
            even_hour = target_at.hour - (target_at.hour % 2)
            lookup_at = target_at.replace(hour=even_hour, minute=0, second=0, microsecond=0)
            record = _forecast_qs_for_point(wp).filter(forecast_at=lookup_at).first()
            if record is None:
                record = (
                    _forecast_qs_for_point(wp)
                    .filter(forecast_at__gte=lookup_at - timedelta(hours=2), forecast_at__lte=lookup_at + timedelta(hours=2))
                    .order_by("forecast_at")
                    .first()
                )
        elif wp:
            # Timing pending: use midday sample so the UI still shows point weather without fake ETA.
            record = (
                _forecast_qs_for_point(wp)
                .filter(forecast_at__date=selected_date, forecast_at__hour=12)
                .order_by("forecast_at")
                .first()
            )
            if record is None:
                record = (
                    _forecast_qs_for_point(wp)
                    .filter(forecast_at__date=selected_date)
                    .order_by("forecast_at")
                    .first()
                )
        weather = reading_payload(record, now=local) if record else None
        arrival_state = weather["severity"] if weather else "normal"
        if arrival is not None:
            if arrival >= 900:
                arrival_state = "critical"
            elif arrival >= 720 and arrival_state == "normal":
                arrival_state = "change"
        planned.append(
            {
                **serialize_point(point),
                "arrival_minutes": arrival,
                "time": format_hhmm(arrival) if arrival is not None else "—",
                "timing_estimated": route.timing_status == Route.TimingStatus.ESTIMATED,
                "timing_pending": timing_pending or point.timing_status == RoutePoint.TimingStatus.PENDING,
                "weather": weather,
                "temp": weather["temperature_c"] if weather else None,
                "wind": weather["wind_speed_kmh"] if weather else None,
                "icon": weather["icon"] if weather else "☼",
                "condition": weather["condition"] if weather else point.note,
                "state": arrival_state,
                "note": point.note or ("زمان‌بندی مسیر هنوز نهایی نشده" if timing_pending else ""),
            }
        )

    dest_point = destination_weather_point(route.destination)
    dest_records = _records_for_day(dest_point, selected_date) if dest_point else []
    hourly = _hourly_for_period(dest_point, selected_date, period, now=local) if dest_point else []
    if not timing_pending and any(item["state"] == "critical" for item in planned):
        for payload in hourly:
            if payload["hour"] >= 8:
                payload["state"] = "critical"
                payload["severity"] = "critical"

    finish = planned[-1] if planned else None
    critical_point = next((item for item in planned if item["state"] == "critical"), finish)
    summary_state = "critical" if any(item["state"] == "critical" for item in planned) else "change" if any(item["state"] == "change" for item in planned) else "normal"
    state_label = {"critical": "هشدار", "change": "احتیاط", "normal": "حرکت مناسب"}[summary_state]
    if summary_state == "critical" and critical_point:
        state_summary = f"در حوالی {critical_point['name']} شرایط پرریسک می‌شود؛ امکان برگشت را از قبل در برنامه نگه دار."
        hero_status = f"نقطهٔ حساس: {critical_point['name']} · {critical_point['note']} · حوالی {critical_point['time']}"
    elif summary_state == "change" and critical_point:
        state_summary = f"از حوالی {critical_point['name']} تغییر شرایط شروع می‌شود؛ زمان برگشت و تجهیزات را جدی‌تر چک کن."
        hero_status = f"تغییر مهم: {critical_point['name']} · حوالی {critical_point['time']}"
    else:
        state_summary = "شرایط مسیر برای شروع آرام‌تر است؛ همچنان پیش‌بینی نقطه‌های بالاتر را دنبال کن."
        hero_status = "شرایط مسیر فعلاً آرام‌تر است"
        critical_point = finish

    recommendations = []
    if timing_pending:
        recommendations.append("زمان‌بندی دقیق مسیر هنوز نهایی نشده؛ ETA و مسافت تجمعی فعلاً در دسترس نیست.")
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
        decision_title = f"با حرکت ساعت {start_label}، زمان رسیدن هنوز مشخص نیست (timing pending)."
        duration_label = "نامشخص"
        arrival_label = "—"
    else:
        duration = round((route.round_trip_minutes or 0) * multiplier) if route.round_trip_minutes else None
        duration_label = format_duration(duration) if duration else "—"
        arrival_label = finish_label
        decision_title = f"با حرکت ساعت {start_label}، حدود {finish_label} به مقصد می‌رسی."

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
        {"label": "زمان رفت‌وبرگشت", "value": duration_label},
        {"label": "رسیدن به مقصد", "value": arrival_label},
    ]
    return {
        "route": serialize_route(route),
        "days": days,
        "period": PERIODS[period],
        "start_minutes": start_minutes,
        "start_time": start_label,
        "speed": speed,
        "speed_options": list(SPEED_MULTIPLIERS.keys()),
        "timing_pending": timing_pending,
        "timing_status": route.timing_status,
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
            },
        ),
    }


def list_destinations(*, query: str = "") -> list[Destination]:
    qs = Destination.objects.filter(is_active=True).order_by("popular_order", "slug")
    if query:
        normalized = query.strip().replace("ي", "ی").replace("ك", "ک").lower()
        qs = [
            item
            for item in qs
            if normalized in item.name.lower()
            or normalized in item.tile_name.lower()
            or normalized in item.short_category.lower()
            or normalized in item.category.lower()
        ]
        return qs[:6]
    return list(qs)


def get_destination(slug: str) -> Destination:
    try:
        return Destination.objects.get(slug=slug, is_active=True)
    except Destination.DoesNotExist as exc:
        raise NotFound({"detail": "مقصد پیدا نشد."}) from exc


def get_route_point(route_slug: str, point_slug: str) -> RoutePoint:
    try:
        return RoutePoint.objects.select_related("route", "route__destination", "weather_point").get(
            route__slug=route_slug,
            slug=point_slug,
        )
    except RoutePoint.DoesNotExist as exc:
        raise NotFound({"detail": "نقطهٔ مسیر پیدا نشد."}) from exc


def route_point_forecast(
    route_point: RoutePoint,
    *,
    selected_date: date,
    period: str,
    back_params: dict | None = None,
) -> dict:
    refresh_if_bucket_changed()
    local = now_tehran()
    today = local.date()
    route = route_point.route
    wp = route_point.weather_point
    weather = None
    hourly: list[dict] = []
    empty_weather = wp is None
    if wp:
        hourly = _hourly_for_period(wp, selected_date, period, now=local)
        if hourly:
            weather = hourly[min(len(hourly) // 2, len(hourly) - 1)]
        else:
            empty_weather = True
    elevation = route_point.effective_elevation_m
    location = route_point.effective_location
    back_query_parts = [f"date={selected_date.isoformat()}", f"period={period}"]
    if back_params:
        for key in ("start_time", "speed"):
            value = back_params.get(key)
            if value:
                back_query_parts.append(f"{key}={value}")
    back_query = "&".join(back_query_parts)
    return {
        "point": {
            **serialize_point(route_point),
            "route_slug": route.slug,
            "route_title": route.title,
            "route_href": f"/routes/{route.slug}",
            "destination": serialize_destination(route.destination),
            "has_weather_point": wp is not None,
            "has_forecast": bool(hourly),
            "latitude": location.y if location else None,
            "longitude": location.x if location else None,
            "elevation_m": elevation,
            "elevation_label": f"{to_fa_digits(elevation)} m" if elevation is not None else "ارتفاع نامشخص",
        },
        "days": [day_payload(day, today) for day in day_window(today)],
        "period": PERIODS[period],
        "weather": weather,
        "hourly": hourly,
        "empty": empty_weather and not hourly,
        "partial": wp is not None and not hourly,
        "back_href": f"/routes/{route.slug}?{back_query}",
        "meta": meta_base(selected_date=selected_date, period=period),
    }


def get_route(slug: str) -> Route:
    try:
        return Route.objects.select_related("destination").get(slug=slug)
    except Route.DoesNotExist as exc:
        raise NotFound({"detail": "مسیر پیدا نشد."}) from exc

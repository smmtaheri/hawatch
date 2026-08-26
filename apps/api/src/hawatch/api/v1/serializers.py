from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings
from rest_framework.exceptions import NotFound

from hawatch.common.time import (
    PERIODS,
    SPEED_MULTIPLIERS,
    day_payload,
    day_window,
    format_clock,
    format_duration,
    format_hhmm,
    hour_flags,
    now_tehran,
    to_fa_digits,
    timezone,
)
from hawatch.integrations.weather.demo import wind_compass
from hawatch.modules.catalog.seed import refresh_if_bucket_changed
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import DemoSeedState, ForecastRecord, WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint


def meta_base(*, selected_date: date, period: str, extra: dict | None = None) -> dict:
    local = now_tehran()
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
        "data_mode": "demo" if settings.DEMO_DATA_ENABLED else "live",
        "provider": "demo" if settings.DEMO_DATA_ENABLED else "internal",
        "source": "hawatch-demo" if settings.DEMO_DATA_ENABLED else "internal",
        "seed_version": settings.DEMO_SEED_VERSION,
        "freshness": freshness,
        "generated_at": state.generated_at.isoformat() if state else local.isoformat(),
        "last_generated_time": state.generated_at.isoformat() if state else None,
        "forecast_validity": {
            "valid_from": (selected_date.isoformat() + "T00:00:00"),
            "valid_to": ((selected_date + timedelta(days=1)).isoformat() + "T00:00:00"),
        },
    }
    if extra:
        payload.update(extra)
    return payload


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
    return {
        "slug": route.slug,
        "title": route.title,
        "trail_label": route.trail_label,
        "origin": route.origin,
        "destination_label": route.destination_label,
        "distance_km": float(route.distance_km),
        "distance_label": f"{to_fa_digits(route.distance_km)} km",
        "ascent_m": route.ascent_m,
        "ascent_label": f"{to_fa_digits(route.ascent_m)} m",
        "featured": route.featured,
        "href": f"/routes/{route.slug}",
    }


def serialize_route(route: Route) -> dict:
    points = list(route.points.select_related("destination").all())
    siblings = [
        serialize_route_summary(item)
        for item in Route.objects.filter(destination=route.destination).exclude(pk=route.pk).order_by("sort_order")
    ]
    return {
        "slug": route.slug,
        "title": route.title,
        "subtitle": route.subtitle,
        "trail_label": route.trail_label,
        "origin": route.origin,
        "destination_label": route.destination_label,
        "region": route.region,
        "distance_km": float(route.distance_km),
        "distance_label": f"{to_fa_digits(route.distance_km)} km",
        "ascent_m": route.ascent_m,
        "ascent_label": f"{to_fa_digits(route.ascent_m)} m",
        "round_trip_minutes": route.round_trip_minutes,
        "default_start_minutes": route.default_start_minutes,
        "featured": route.featured,
        "href": f"/routes/{route.slug}",
        "parent": serialize_destination(route.destination),
        "points": [serialize_point(point) for point in points],
        "siblings": siblings,
    }


def serialize_point(point: RoutePoint) -> dict:
    return {
        "slug": point.slug,
        "name": point.name,
        "elevation_m": point.elevation_m,
        "elevation_label": f"{to_fa_digits(point.elevation_m)} m",
        "base_minutes": point.base_minutes,
        "sort_order": point.sort_order,
        "note": point.note,
        "axis_x": point.axis_x,
        "axis_y": point.axis_y,
        "href": f"/destination-point/{point.slug}",
        "latitude": point.location.y,
        "longitude": point.location.x,
    }


def reading_payload(record: ForecastRecord, *, today: date, current_hour: int) -> dict:
    local_at = record.forecast_at.astimezone(timezone())
    flags = hour_flags(local_at.date(), local_at.hour, today, current_hour)
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
        "wind_direction_deg": record.wind_direction_deg,
        "wind_direction_label": wind_compass(record.wind_direction_deg),
        "precipitation_probability": record.precipitation_probability,
        "precipitation_mm": float(record.precipitation_mm),
        "visibility_km": float(record.visibility_km),
        "cloud_cover_pct": record.cloud_cover_pct,
        "uv_index": record.uv_index,
        "freezing_level_m": record.freezing_level_m,
        "cloud_base_m": record.cloud_base_m,
        "severity": record.severity,
        "state": record.severity,
        "freshness": record.freshness,
        **flags,
    }


def _uv_label(uv: int) -> str:
    if uv >= 8:
        level = "خیلی زیاد"
    elif uv >= 6:
        level = "زیاد"
    elif uv >= 3:
        level = "متوسط"
    else:
        level = "کم"
    return f"{to_fa_digits(uv)} · {level}"


def destination_forecast(destination: Destination, *, selected_date: date, period: str) -> dict:
    refresh_if_bucket_changed()
    local = now_tehran()
    today = local.date()
    point = WeatherPoint.objects.get(slug=f"dest:{destination.slug}")
    start = localize_dt_safe(selected_date, 0)
    end = start + timedelta(days=1)
    records = list(
        ForecastRecord.objects.filter(weather_point=point, forecast_at__gte=start, forecast_at__lt=end).order_by("forecast_at")
    )
    hours_spec = PERIODS[period]["hours"]
    hourly = []
    for record in records:
        hour = record.forecast_at.astimezone(timezone()).hour
        if hour in hours_spec:
            hourly.append(reading_payload(record, today=today, current_hour=local.hour))

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
        hero_alert = f"!　تغییر مهم: از ساعت {to_fa_digits(hour)} {change.condition_label}"
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
        uv = max(item.uv_index for item in records)
        precip = max(item.precipitation_probability for item in records)
        freeze = next((item.freezing_level_m for item in records if item.freezing_level_m), destination.elevation_m + 200)
        cloud_base = next((item.cloud_base_m for item in records if item.cloud_base_m), destination.elevation_m + 400)
        sunrise = format_clock(5, 22 if destination.climate != "desert" else 24)
        sunset = format_clock(19, 46 if destination.climate != "desert" else 38)
        metrics = [
            {"icon": "⌁", "label": "باد میانگین", "value": f"{to_fa_digits(avg_wind)} km/h", "note": wind_compass(records[0].wind_direction_deg), "color": "teal"},
            {"icon": "↯", "label": "تندباد", "value": f"{to_fa_digits(gust)} km/h", "note": "بیشتر از ساعت ۱۲" if gust >= 20 else "آرام‌تر", "color": "coral" if gust >= 30 else "teal"},
            {"icon": "◌", "label": "دید افقی", "value": f"+{to_fa_digits(int(vis))} km" if vis >= 10 else f"{to_fa_digits(vis)} km", "note": "کاهش دید در شرایط حساس", "color": "coral" if vis < 6 else "teal"},
            {"icon": "❄", "label": "تراز صفر درجه", "value": f"{to_fa_digits(freeze)} m", "note": "بالاتر از قله" if freeze > destination.elevation_m else "نزدیک سطح", "color": ""},
            {"icon": "☁", "label": "پایهٔ ابر", "value": f"{to_fa_digits(cloud_base)} m", "note": "نسبت به ارتفاع مقصد", "color": ""},
            {"icon": "☀", "label": "تابش فرابنفش", "value": _uv_label(uv), "note": "برای بخش‌های باز مسیر", "color": "amber" if uv >= 6 else "teal"},
            {"icon": "☂", "label": "بارش", "value": f"{to_fa_digits(precip)}٪", "note": "بر اساس بازهٔ انتخابی", "color": "amber" if precip else "teal"},
            {"icon": "◷", "label": "طلوع / غروب", "value": f"{sunrise} / {sunset}", "note": "برای زمان‌بندی برگشت", "color": ""},
        ]

    days = [day_payload(day, today) for day in day_window(today)]
    empty = not records
    return {
        "destination": serialize_destination(destination, include_routes=True),
        "days": days,
        "period": PERIODS[period],
        "current": reading_payload(now_record, today=today, current_hour=local.hour) if now_record else None,
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
        "updated_label": f"آخرین به‌روزرسانی: امروز، {format_clock(local.hour, local.minute)}",
        "empty": empty,
        "meta": meta_base(selected_date=selected_date, period=period),
    }


def localize_dt_safe(value: date, hour: int):
    from hawatch.common.time import localize_dt

    return localize_dt(value, hour)


def route_forecast(route: Route, *, selected_date: date, period: str, start_minutes: int, speed: str) -> dict:
    refresh_if_bucket_changed()
    local = now_tehran()
    today = local.date()
    multiplier = SPEED_MULTIPLIERS[speed]
    points = list(route.points.select_related("weather_point").all())
    planned = []
    for point in points:
        arrival = start_minutes + round(point.base_minutes * multiplier)
        hour = (arrival // 60) % 24
        even_hour = hour - (hour % 2)
        wp = getattr(point, "weather_point", None)
        record = None
        if wp:
            start = localize_dt_safe(selected_date, even_hour)
            record = ForecastRecord.objects.filter(weather_point=wp, forecast_at=start).first()
            if record is None:
                record = (
                    ForecastRecord.objects.filter(weather_point=wp, forecast_at__date=selected_date)
                    .order_by("forecast_at")
                    .first()
                )
        weather = reading_payload(record, today=today, current_hour=local.hour) if record else None
        arrival_state = weather["severity"] if weather else "normal"
        if arrival >= 900:
            arrival_state = "critical"
        elif arrival >= 720 and arrival_state == "normal":
            arrival_state = "change"
        planned.append(
            {
                **serialize_point(point),
                "arrival_minutes": arrival,
                "time": format_hhmm(arrival),
                "weather": weather,
                "temp": weather["temperature_c"] if weather else None,
                "wind": weather["wind_speed_kmh"] if weather else None,
                "icon": weather["icon"] if weather else "☼",
                "condition": weather["condition"] if weather else point.note,
                "state": arrival_state,
                "note": point.note,
            }
        )

    dest_point = WeatherPoint.objects.get(slug=f"dest:{route.destination.slug}")
    dest_records = list(
        ForecastRecord.objects.filter(
            weather_point=dest_point,
            forecast_at__gte=localize_dt_safe(selected_date, 0),
            forecast_at__lt=localize_dt_safe(selected_date, 0) + timedelta(days=1),
        ).order_by("forecast_at")
    )
    hours_spec = PERIODS[period]["hours"]
    hourly = []
    for record in dest_records:
        hour = record.forecast_at.astimezone(timezone()).hour
        if hour in hours_spec:
            payload = reading_payload(record, today=today, current_hour=local.hour)
            if any(item["state"] == "critical" for item in planned):
                if hour >= 8:
                    payload["state"] = "critical"
                    payload["severity"] = "critical"
            hourly.append(payload)

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
    if summary_state == "critical":
        recommendations.append("اگر رعدوبرق، باد شدید یا دید محدود فعال است، صعود را ادامه نده و زودتر برگرد.")
    if critical_point and (critical_point.get("wind") or 0) >= 25:
        recommendations.append("باد در بخش حساس بالاست؛ بندهای کوله و باتوم را محکم کن و روی یال توقف طولانی نداشته باش.")
    if critical_point and (critical_point.get("temp") is not None and critical_point["temp"] <= 2):
        recommendations.append("دستکش گرم، لایهٔ عایق و عینک محافظ همراه داشته باش؛ در ارتفاع توقف طولانی نکن.")
    if not recommendations:
        recommendations.append("یک لایهٔ اضافه، آب کافی و چراغ پیشانی همراه داشته باش؛ شرایط فعلاً آرام‌تر است.")

    duration = round(route.round_trip_minutes * multiplier)
    start_label = format_hhmm(start_minutes)
    finish_label = finish["time"] if finish else "—"
    days = [day_payload(day, today) for day in day_window(today)]
    return {
        "route": serialize_route(route),
        "days": days,
        "period": PERIODS[period],
        "start_minutes": start_minutes,
        "start_time": start_label,
        "speed": speed,
        "speed_options": list(SPEED_MULTIPLIERS.keys()),
        "points": planned,
        "hourly": hourly,
        "hero": {"status": hero_status},
        "stats": [
            {"label": "مسافت", "value": f"{to_fa_digits(route.distance_km)} km"},
            {"label": "صعود", "value": f"{to_fa_digits(route.ascent_m)} m"},
            {"label": "زمان رفت‌وبرگشت", "value": format_duration(duration)},
            {"label": "رسیدن به مقصد", "value": finish_label},
        ],
        "decision": {
            "chip": f"پیش‌بینی مسیر · {day_payload(selected_date, today)['label']}",
            "title": f"با حرکت ساعت {start_label}، حدود {finish_label} به مقصد می‌رسی.",
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
        },
        "empty": not planned,
        "meta": meta_base(
            selected_date=selected_date,
            period=period,
            extra={"selected_start_time": start_label, "selected_speed": speed},
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


def get_route(slug: str) -> Route:
    try:
        return Route.objects.select_related("destination").get(slug=slug)
    except Route.DoesNotExist as exc:
        raise NotFound({"detail": "مسیر پیدا نشد."}) from exc

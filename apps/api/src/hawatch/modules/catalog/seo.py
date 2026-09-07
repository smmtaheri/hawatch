"""Small, data-derived SEO copy builders shared by catalog and HTML views.

The catalog identity is the source for a page subject.  Forecast wording is
only added when there is an actual persisted forecast window; no provider
claim, date range, or editorial paragraph is invented for a sparse record.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone as django_timezone

from hawatch.common.time import now_tehran, to_fa_digits
from hawatch.modules.catalog.identity import place_type_label
from hawatch.modules.forecasts.models import ForecastRecord, WeatherPoint
from hawatch.modules.routes.models import Route


def _bounded_copy(value: str, limit: int) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1].rstrip()}…"


@dataclass(frozen=True)
class ForecastSeoContext:
    days: int | None
    source: str | None
    generated_at: datetime | None
    temperature_c: int | None = None
    condition_label: str | None = None
    icon: str | None = None

    @property
    def duration_label(self) -> str | None:
        if not self.days:
            return None
        return f"پیش‌بینی {to_fa_digits(self.days)} روز آینده"


def point_forecast_context(point: WeatherPoint) -> ForecastSeoContext:
    """Return only the real, future forecast coverage available for a point."""

    now = django_timezone.now()
    records = ForecastRecord.objects.filter(weather_point=point, forecast_at__gte=now)
    first = records.order_by("forecast_at").only(
        "forecast_at",
        "source",
        "generated_at",
        "temperature_c",
        "condition_label",
        "icon",
    ).first()
    if first is None:
        return ForecastSeoContext(days=None, source=None, generated_at=None)
    last = records.order_by("-forecast_at").only("forecast_at").first()
    day_count = (last.forecast_at.astimezone(now_tehran().tzinfo).date() - first.forecast_at.astimezone(now_tehran().tzinfo).date()).days + 1
    return ForecastSeoContext(
        days=max(1, day_count),
        source=first.source or None,
        generated_at=first.generated_at,
        temperature_c=first.temperature_c,
        condition_label=first.condition_label or None,
        icon=first.icon or None,
    )


def point_subject(point: WeatherPoint) -> str:
    """Use a localized type once, without making ``قلهٔ قلهٔ …``."""

    name = point.page_name or point.name
    place_type = place_type_label(point.place_type)
    return name if place_type in name else f"{place_type} {name}"


def point_subtitle(point: WeatherPoint, *, forecast: ForecastSeoContext | None = None) -> str:
    subject = point_subject(point)
    pieces = [f"پیش‌بینی آب‌وهوای {subject}"]
    if point.elevation_m is not None:
        pieces.append(f"در ارتفاع {to_fa_digits(point.elevation_m)} متر")
    context = forecast or point_forecast_context(point)
    if context.duration_label:
        pieces.append(context.duration_label)
    return " ".join(pieces)


def point_seo_copy(point: WeatherPoint) -> dict[str, str | None]:
    forecast = point_forecast_context(point)
    subtitle = point_subtitle(point, forecast=forecast)
    region = f" در {point.region}" if point.region else ""
    description = f"{subtitle}{region}."
    if forecast.duration_label:
        description += " داده‌های موجود و مسیرهای مرتبط در هواچ."
    else:
        description += " اطلاعات نقطه و مسیرهای مرتبط در هواچ."
    forecast_summary = None
    if forecast.temperature_c is not None and forecast.condition_label:
        forecast_summary = (
            f"{forecast.icon or ''} {forecast.condition_label}؛ حدود "
            f"{to_fa_digits(forecast.temperature_c)} درجه در نزدیک‌ترین بازهٔ پیش‌بینی."
        ).strip()
    return {
        "title": _bounded_copy(point.seo_title.strip() or f"{subtitle} | هواچ", 160),
        "description": _bounded_copy(point.seo_description.strip() or description, 320),
        "subtitle": subtitle,
        "content": point.seo_content.strip() or None,
        "forecast_duration": forecast.duration_label,
        "forecast_source": forecast.source,
        "forecast_generated_at": forecast.generated_at,
        "forecast_summary": forecast_summary,
    }


def route_seo_copy(route: Route) -> dict[str, str | None]:
    subject = route.title
    duration = f"زمان یک‌طرفه حدود {to_fa_digits(route.one_way_minutes)} دقیقه" if route.one_way_minutes else None
    subtitle = f"پیش‌بینی آب‌وهوا در مسیر {subject} از {route.origin} تا {route.target_label}"
    pieces = [subtitle]
    if route.region:
        pieces.append(f"منطقهٔ {route.region}")
    if route.distance_km is not None:
        pieces.append(f"مسافت {to_fa_digits(route.distance_km)} کیلومتر")
    if duration:
        pieces.append(duration)
    description = "؛ ".join(pieces) + "."
    forecast = point_forecast_context(route.target_weather_point) if route.target_weather_point_id else None
    forecast_summary = None
    if forecast and forecast.temperature_c is not None and forecast.condition_label:
        forecast_summary = (
            f"{forecast.icon or ''} {forecast.condition_label}؛ حدود "
            f"{to_fa_digits(forecast.temperature_c)} درجه در نزدیک‌ترین بازهٔ مقصد."
        ).strip()
    return {
        "title": _bounded_copy(route.seo_title.strip() or f"{subtitle} | هواچ", 160),
        "description": _bounded_copy(route.seo_description.strip() or description, 320),
        "subtitle": subtitle,
        "content": route.seo_content.strip() or None,
        "forecast_summary": forecast_summary,
    }

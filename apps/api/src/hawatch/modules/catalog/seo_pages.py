"""Server-rendered public HTML for crawlers and JavaScript-disabled clients.

The React application remains the interactive surface.  These views only own
the document head and a small semantic fallback which is replaced by React
after ``/assets/hawatch.js`` loads.  They intentionally read the runtime
database, rather than catalog fixtures, so an imported Point or Route becomes
SEO-ready without adding a hard-coded URL to the frontend build.
"""

from __future__ import annotations

import re
from decimal import Decimal

from django.conf import settings
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from hawatch.modules.catalog.identity import place_type_label
from hawatch.modules.catalog.runtime import publicly_visible_weather_points
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route


HOME_TITLE = "هواچ | هوای نقطه، برنامهٔ مسیر"
HOME_DESCRIPTION = "هواچ؛ هوای نقاط و برنامهٔ مسیر."
_PLACE_TYPE_TOKEN_RE = re.compile(r"(نقطهٔ\s+)([a-z][a-z0-9_]*)", re.IGNORECASE)


def _canonical(path: str) -> str:
    return f"{settings.PUBLIC_SITE_ORIGIN}{path}"


def _robots(request: HttpRequest) -> str:
    """Planner/query variants remain crawlable for links but never indexed."""

    return "noindex,follow" if request.GET else "index,follow"


def _format_decimal(value: Decimal | None, suffix: str) -> str | None:
    if value is None:
        return None
    return f"{value.normalize()} {suffix}"


def _localized_identity_summary(point: WeatherPoint) -> str:
    """Hide stable English enum codes from the public semantic HTML."""

    summary = point.identity_summary or f"{point.page_name or point.name}؛ نقطهٔ {point.place_type}"

    def replace(match: re.Match[str]) -> str:
        return f"{match.group(1)}{place_type_label(match.group(2))}"

    return _PLACE_TYPE_TOKEN_RE.sub(replace, summary)


def _render(request: HttpRequest, *, page: dict, status: int = 200) -> HttpResponse:
    robots = _robots(request) if status == 200 else "noindex,follow"
    response = render(
        request,
        "catalog/seo_page.html",
        {
            "page": page,
            "robots": robots,
        },
        status=status,
    )
    # Match the HTML directive for non-HTML-aware crawlers and ensure catalog
    # edits are revalidated instead of being held by an intermediary cache.
    response["X-Robots-Tag"] = robots
    response["Cache-Control"] = "no-cache"
    response["Content-Language"] = "fa"
    return response


def _not_found(request: HttpRequest, *, content_type: str) -> HttpResponse:
    label = "نقطه" if content_type == "point" else "مسیر"
    return _render(
        request,
        status=404,
        page={
            "kind": "not-found",
            "title": "صفحه پیدا نشد | هواچ",
            "description": "آدرس واردشده در هواچ معتبر نیست یا دیگر در دسترس نیست.",
            "headline": f"{label} پیدا نشد",
            "summary": "از جست‌وجوی هواچ یک نقطه یا مسیر دیگر را انتخاب کنید.",
            "canonical": "",
        },
    )


def _point_page(point: WeatherPoint) -> dict:
    name = point.page_name or point.name
    route_filter = (
        Q(points__weather_point=point)
        | Q(origin_weather_point=point)
        | Q(target_weather_point=point)
    )
    # A primary Point can represent a destination whose physical endpoint is
    # a named shore/landing WeatherPoint (for example, Lake Gahar).  The
    # catalog's explicit target label is the only fallback used here.
    if point.kind == WeatherPoint.Kind.PRIMARY:
        route_filter |= Q(target_label=point.name) | Q(target_label=name)
    route_rows = (
        Route.objects.filter(route_filter, is_active=True)
        .distinct()
        .order_by("sort_order", "slug")
    )
    return {
        "kind": "point",
        "title": f"هوای {name} | هواچ",
        "description": f"پیش‌بینی هوا و وضعیت مسیر برای {name} در هواچ.",
        "canonical": _canonical(f"/points/{point.slug}"),
        "headline": name,
        "summary": _localized_identity_summary(point) or f"پیش‌بینی هوا و اطلاعات مسیرهای مرتبط با {name} در هواچ.",
        "region": point.region,
        "category": point.category,
        "place_type": place_type_label(point.place_type),
        "elevation": f"{point.elevation_m} متر" if point.elevation_m is not None else "ارتفاع نامشخص",
        "routes": [
            {
                "title": route.title,
                "href": f"/routes/{route.slug}",
                "description": f"از {route.origin} تا {route.target_label}",
            }
            for route in route_rows
        ],
    }


def _route_page(route: Route) -> dict:
    route_points = list(route.points.select_related("weather_point").all())
    target_href = f"/points/{route.target_weather_point.slug}" if route.target_weather_point_id else ""
    # Some routes finish at a physical endpoint such as a lake shore while
    # their public target is the canonical primary destination. Resolve that
    # exact catalog label so the semantic route page points to the same
    # canonical destination page as the Point page, without guessing by slug.
    destination = (
        publicly_visible_weather_points()
        .filter(kind=WeatherPoint.Kind.PRIMARY)
        .filter(Q(name=route.target_label) | Q(page_name=route.target_label))
        .only("slug")
        .first()
    )
    if destination is not None:
        target_href = f"/points/{destination.slug}"
    return {
        "kind": "route",
        "title": f"هوای {route.title} | هواچ",
        "description": f"پیش‌بینی هوا و وضعیت مسیر {route.title} در هواچ.",
        "canonical": _canonical(f"/routes/{route.slug}"),
        "headline": route.title,
        "summary": route.subtitle or f"مسیر پیاده‌روی از {route.origin} تا {route.target_label} در {route.region}.",
        "region": route.region,
        "origin": route.origin,
        "target": route.target_label,
        "origin_href": f"/points/{route.origin_weather_point.slug}" if route.origin_weather_point_id else "",
        "target_href": target_href,
        "distance": _format_decimal(route.distance_km, "کیلومتر"),
        "ascent": f"{route.ascent_m} متر" if route.ascent_m is not None else None,
        "points": [
            {
                "name": point.name,
                "href": f"/points/{point.weather_point.slug}",
            }
            for point in route_points
            if point.weather_point_id
        ],
    }


@require_GET
def seo_home(request: HttpRequest) -> HttpResponse:
    popular_points = publicly_visible_weather_points().filter(is_popular=True).order_by("popular_order", "slug")[:4]
    return _render(
        request,
        page={
            "kind": "home",
            "title": HOME_TITLE,
            "description": HOME_DESCRIPTION,
            "canonical": _canonical("/"),
            "headline": "هوای مسیرت را ببین",
            "summary": "هواچ پیش‌بینی هوای نقاط و اطلاعات مسیرهای کوه‌پیمایی را برای برنامه‌ریزی آگاهانه کنار هم می‌آورد.",
            "popular_points": [
                {"name": point.page_name or point.name, "href": f"/points/{point.slug}"}
                for point in popular_points
            ],
        },
    )


@require_GET
def seo_point(request: HttpRequest, slug: str) -> HttpResponse:
    point = publicly_visible_weather_points().filter(slug=slug).first()
    if point is None:
        return _not_found(request, content_type="point")
    return _render(request, page=_point_page(point))


@require_GET
def seo_route(request: HttpRequest, slug: str) -> HttpResponse:
    route = (
        Route.objects.filter(slug=slug, is_active=True)
        .select_related("origin_weather_point", "target_weather_point")
        .first()
    )
    if route is None:
        return _not_found(request, content_type="route")
    return _render(request, page=_route_page(route))

"""Server-rendered public HTML for crawlers and JavaScript-disabled clients.

The React application remains the interactive surface.  These views only own
the document head and a small semantic fallback which is replaced by React
after ``/assets/hawatch.js`` loads.  They intentionally read the runtime
database, rather than catalog fixtures, so an imported destination, Point or
Route becomes SEO-ready without adding a hard-coded URL to the frontend build.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal

from django.conf import settings
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from hawatch.modules.catalog.identity import ACCESS_PLACE_TYPES, place_type_label
from hawatch.modules.catalog.internal_links import (
    related_public_destinations,
    related_public_routes,
    related_public_similar_destinations,
    related_public_villages,
    similar_destinations_title,
)
from hawatch.modules.catalog.runtime import (
    DESTINATIONS_PAGE_SIZE,
    ordered_publicly_visible_destinations,
    publicly_visible_weather_points,
)
from hawatch.modules.catalog.seo import point_seo_copy, route_seo_copy
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route


HOME_TITLE = "هواچ | پیش‌بینی هوای کوهستان و مسیرها"
HOME_DESCRIPTION = "هواچ؛ پیش‌بینی آب‌وهوای قله‌ها، دریاچه‌ها و مسیرهای کوه‌پیمایی برای برنامه‌ریزی بهتر."
DESTINATIONS_TITLE = "مقصدهای اصلی هواچ | قله‌ها، دریاچه‌ها و مسیرها"
DESTINATIONS_DESCRIPTION = "مقصدهای اصلی هواچ؛ پیش‌بینی آب‌وهوای قله‌ها، دریاچه‌ها و عارضه‌های مهم برای برنامه‌ریزی مسیر."
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
    robots = _robots(request) if status == 200 and page.get("indexable", True) else "noindex,follow"
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


def _structured_breadcrumb(*items: tuple[str, str]) -> str:
    """Serialize a valid BreadcrumbList without exposing request-specific URLs."""

    value = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": index, "name": name, "item": _canonical(path)}
            for index, (name, path) in enumerate(items, start=1)
        ],
    }
    # Django's ``safe`` template marker is appropriate only after escaping the
    # three characters that could terminate a script element.
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _structured_website() -> str:
    value = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "هواچ",
        "alternateName": "Hawatch",
        "url": _canonical("/"),
        "description": HOME_DESCRIPTION,
    }
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _structured_destination_list(
    points: list[WeatherPoint],
    *,
    canonical_path: str = "/destinations",
    position_offset: int = 0,
    total: int | None = None,
) -> str:
    value = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": DESTINATIONS_TITLE,
        "url": _canonical(canonical_path),
        "description": DESTINATIONS_DESCRIPTION,
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": total if total is not None else len(points),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position_offset + index,
                    "name": point.page_name or point.name,
                    "url": _canonical(f"/points/{point.slug}"),
                }
                for index, point in enumerate(points, start=1)
            ],
        },
    }
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _not_found(request: HttpRequest, *, content_type: str) -> HttpResponse:
    label = {"point": "نقطه", "route": "مسیر", "destinations": "مقصدها"}.get(content_type, "صفحه")
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
    seo = point_seo_copy(point)
    route_rows = related_public_routes(point)
    has_routes = route_rows.exists()
    destination_rows = related_public_destinations(point) if point.place_type in ACCESS_PLACE_TYPES and not has_routes else ()
    village_rows = related_public_villages(point) if point.place_type not in ACCESS_PLACE_TYPES else ()
    similar_rows = related_public_similar_destinations(point) if not has_routes else ()
    return {
        "kind": "point",
        "title": seo["title"],
        "description": seo["description"],
        "canonical": _canonical(f"/points/{point.slug}"),
        "indexable": bool(point.seo_indexable),
        "headline": seo["h1"],
        "summary": seo["subtitle"],
        "identity_summary": _localized_identity_summary(point),
        "seo_content": seo["content"],
        "forecast_summary": seo["forecast_summary"],
        "structured_data": _structured_breadcrumb(("هواچ", "/"), (point.name, f"/points/{point.slug}")),
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
        "related_destinations": [
            {
                "name": destination.page_name or destination.name,
                "href": f"/points/{destination.slug}",
            }
            for destination in destination_rows
        ],
        "related_villages": [
            {
                "name": village.page_name or village.name,
                "href": f"/points/{village.slug}",
            }
            for village in village_rows
        ],
        "similar_destinations": [
            {
                "name": destination.page_name or destination.name,
                "href": f"/points/{destination.slug}",
            }
            for destination in similar_rows
        ],
        "similar_destinations_title": similar_destinations_title(point),
    }


def _route_page(route: Route) -> dict:
    seo = route_seo_copy(route)
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
        "title": seo["title"],
        "description": seo["description"],
        "canonical": _canonical(f"/routes/{route.slug}"),
        "headline": route.title,
        "summary": seo["subtitle"],
        "identity_summary": route.subtitle,
        "seo_content": seo["content"],
        "forecast_summary": seo.get("forecast_summary"),
        "structured_data": _structured_breadcrumb(("هواچ", "/"), (route.title, f"/routes/{route.slug}")),
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


def _destinations_page(page_number: int = 1) -> dict:
    paginator = Paginator(ordered_publicly_visible_destinations(), DESTINATIONS_PAGE_SIZE)
    page = paginator.page(page_number)
    points = list(page.object_list)
    canonical_path = "/destinations" if page.number == 1 else f"/destinations/page/{page.number}"
    title = DESTINATIONS_TITLE if page.number == 1 else f"{DESTINATIONS_TITLE} | بخش {page.number}"
    return {
        "kind": "destinations",
        "title": title,
        "description": DESTINATIONS_DESCRIPTION,
        "canonical": _canonical(canonical_path),
        "indexable": True,
        "headline": "مقصدهای اصلی هواچ",
        "summary": "قله‌ها، دریاچه‌ها و عارضه‌های مستقلی را ببین که برایشان پیش‌بینی هوا و اطلاعات مسیر در هواچ ثبت شده است.",
        "structured_data": _structured_destination_list(
            points,
            canonical_path=canonical_path,
            position_offset=(page.number - 1) * DESTINATIONS_PAGE_SIZE,
            total=paginator.count,
        ),
        "previous_destinations_href": (
            "/destinations"
            if page.number == 2
            else f"/destinations/page/{page.previous_page_number()}"
            if page.has_previous()
            else None
        ),
        "next_destinations_href": f"/destinations/page/{page.next_page_number()}" if page.has_next() else None,
        "destinations": [
            {
                "name": point.page_name or point.name,
                "href": f"/points/{point.slug}",
                "place_type": place_type_label(point.place_type),
                "region": point.region,
                "elevation": f"{point.elevation_m} متر" if point.elevation_m is not None else None,
            }
            for point in points
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
            "headline": "پیش‌بینی هوای نقاط و مسیرها",
            "summary": "هواچ پیش‌بینی هوای نقاط و اطلاعات مسیرهای کوه‌پیمایی را برای برنامه‌ریزی آگاهانه کنار هم می‌آورد.",
            "structured_data": _structured_website(),
            "destinations_href": "/destinations",
            "popular_points": [
                {"name": point.page_name or point.name, "href": f"/points/{point.slug}"}
                for point in popular_points
            ],
        },
    )


@require_GET
def seo_point(request: HttpRequest, slug: str) -> HttpResponse:
    point = WeatherPoint.objects.filter(slug=slug, is_active=True).first()
    if point is None:
        return _not_found(request, content_type="point")
    return _render(request, page=_point_page(point))


@require_GET
def seo_destinations(request: HttpRequest, page: int = 1) -> HttpResponse:
    if page < 1:
        return _not_found(request, content_type="destinations")
    try:
        destination_page = _destinations_page(page)
    except EmptyPage:
        return _not_found(request, content_type="destinations")
    return _render(request, page=destination_page)


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

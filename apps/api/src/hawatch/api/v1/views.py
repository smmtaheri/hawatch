from __future__ import annotations

from datetime import timedelta, timezone as dt_timezone

from django.db import connection
from django.db.models import Max, OuterRef, Subquery
from django.http import HttpResponse
from django.utils import timezone as dj_timezone
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from hawatch.api.v1.serializers import (
    get_point,
    get_route,
    get_weather_point,
    list_points,
    meta_base,
    point_forecast,
    route_forecast,
    serialize_point_profile,
    serialize_route,
)
from hawatch.modules.catalog.search import search_suggestions
from hawatch.common.time import (
    StartTimeValidationError,
    default_forecast_selection,
    now_tehran,
    parse_date,
    parse_period,
    parse_speed,
    resolve_planner_start_minutes,
)
from hawatch.common.observability import metrics_authorized, metrics_view, set_health
from hawatch.modules.catalog.runtime import (
    destination_catalog_timestamp_points,
    publicly_visible_destinations,
    publicly_visible_weather_points,
)
from hawatch.modules.catalog.seed import refresh_if_bucket_changed
from hawatch.modules.forecasts.models import ForecastSnapshot, ForecastRecord, WeatherPoint
from hawatch.modules.routes.models import Route
from hawatch.integrations.weather.ingest import snapshot_freshness
from hawatch.modules.accounts.services import decorate_forecast_payload, resolve_forecast_access


@api_view(["GET"])
def health_live(_request):
    set_health("live", True)
    return Response({"status": "live"})


@api_view(["GET"])
def health_ready(_request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.execute("SELECT PostGIS_Version()")
            version = cursor.fetchone()[0]
    except Exception:
        set_health("ready", False)
        return Response({"status": "not_ready", "database": "unavailable", "postgis": False}, status=503)
    set_health("ready", True)
    return Response({"status": "ready", "database": "ok", "postgis": True, "postgis_version": version})


@api_view(["GET"])
def health_status(request):
    """Return a small authenticated, DB-backed pilot operations summary."""

    if not metrics_authorized(request):
        return Response({"detail": "Metrics authentication required."}, status=401)

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT PostGIS_Version()")
            postgis_version = cursor.fetchone()[0]

        now = dj_timezone.now()
        snapshots = ForecastSnapshot.objects.filter(provider="open-meteo")
        latest_attempt = snapshots.order_by("-generated_at").first()
        latest_usable = snapshots.filter(status__in=["success", "partial"]).order_by("-generated_at").first()
        freshness = snapshot_freshness(latest_usable)
        age_seconds = None
        if latest_usable is not None:
            age_seconds = max(0, int((now - latest_usable.generated_at).total_seconds()))
        recent_failures = snapshots.filter(
            status=ForecastSnapshot.Status.FAILED,
            generated_at__gte=now - timedelta(hours=24),
        ).count()
        live_records = ForecastRecord.objects.filter(data_mode="live", provider="open-meteo").count()
        catalog = {
            "points": WeatherPoint.objects.filter(is_active=True).count(),
            "routes": Route.objects.filter(is_active=True).count(),
            "weather_points": publicly_visible_weather_points().count(),
        }
        forecast = {
            "provider": "open-meteo",
            "freshness": freshness,
            "latest_attempt_status": latest_attempt.status if latest_attempt else None,
            "latest_attempt_at": now_tehran(latest_attempt.generated_at).isoformat() if latest_attempt else None,
            "latest_usable_at": now_tehran(latest_usable.generated_at).isoformat() if latest_usable else None,
            "age_seconds": age_seconds,
            "point_count": latest_usable.point_count if latest_usable else 0,
            "requested_point_count": latest_usable.requested_point_count if latest_usable else 0,
            "live_record_count": live_records,
            "last_retry_count": latest_attempt.retry_count if latest_attempt else 0,
            "failed_runs_last_24h": recent_failures,
        }
        status = "ok" if latest_usable and freshness in {"ready", "partial"} else "degraded"
        return Response(
            {
                "status": status,
                "database": "ok",
                "postgis": True,
                "postgis_version": postgis_version,
                "catalog": catalog,
                "forecast": forecast,
            }
        )
    except Exception:
        set_health("status", False)
        return Response({"status": "unavailable", "database": "unavailable", "postgis": False}, status=503)


@api_view(["GET"])
def points_list(request):
    refresh_if_bucket_changed()
    query = request.query_params.get("query", "")
    items = list_points(query=query)
    today = now_tehran().date()
    catalog_counts = {
        "points": WeatherPoint.objects.filter(is_active=True).count(),
        "routes": Route.objects.filter(is_active=True).count(),
    }
    return Response(
        {
            "results": [serialize_point_profile(item) for item in items],
            "empty": not items,
            "query": query,
            "meta": meta_base(
                selected_date=today,
                period="morning",
                extra={"catalog_counts": catalog_counts},
            ),
        }
    )


@api_view(["GET"])
def catalog_index(request):
    """Small application catalog payload used by internal search/consumers."""

    refresh_if_bucket_changed()
    return Response(
        {
            "points": [
                serialize_point_profile(point)
                for point in publicly_visible_weather_points().order_by("place_type", "page_name", "name")
            ],
            "routes": [
                {"title": route.title, "origin": route.origin, "target_label": route.target_label, "href": f"/routes/{route.slug}", "region": route.region}
                for route in Route.objects.filter(is_active=True).order_by("region", "sort_order", "slug")
            ],
        }
    )


@api_view(["GET"])
def destinations_index(request):
    """Return only independent, indexable destination points for the hub."""

    refresh_if_bucket_changed()
    destinations = publicly_visible_destinations().order_by(
        "-is_popular",
        "popular_order",
        "page_name",
        "slug",
    )
    return Response({"destinations": [serialize_point_profile(point) for point in destinations]})


@api_view(["GET"])
def point_detail(request, slug: str):
    refresh_if_bucket_changed()
    point = get_point(slug)
    today = now_tehran().date()
    return Response(
        {
            "point": serialize_point_profile(point, include_routes=True),
            "meta": meta_base(selected_date=today, period="morning"),
        }
    )


def _resolve_date_period(request) -> tuple:
    local = now_tehran()
    explicit_date = "date" in request.query_params
    explicit_period = "period" in request.query_params
    default_date, default_period = default_forecast_selection(local)
    selected = parse_date(request.query_params.get("date"), default_date) if explicit_date else default_date
    period = parse_period(request.query_params.get("period")) if explicit_period else default_period
    access = resolve_forecast_access(request, today=local.date())
    # A clean public URL always resolves to the last date this viewer can read;
    # it never writes a query variant merely to enforce the access policy.
    if not explicit_date and selected > access.available_through:
        selected = access.available_through
    return selected, period, access


def _forecast_access_denied(access, selected):
    return Response(
        {
            "code": access.status_for(selected),
            "detail": "برای دیدن پیش‌بینی این روز وارد شوید یا طرح خود را ارتقا دهید.",
            "forecast_access": access.payload(),
        },
        status=403,
        headers={"Cache-Control": "private, no-store", "Vary": "Cookie"},
    )


def _private_forecast(payload, access):
    return Response(
        decorate_forecast_payload(payload, access),
        headers={"Cache-Control": "private, no-store", "Vary": "Cookie"},
    )


@api_view(["GET"])
def route_detail(request, slug: str):
    refresh_if_bucket_changed()
    route = get_route(slug)
    today = now_tehran().date()
    return Response({"route": serialize_route(route), "meta": meta_base(selected_date=today, period="morning")})


def _resolve_start_minutes(request, selected_date, period, local):
    raw_start = request.query_params.get("start_time") if "start_time" in request.query_params else None
    try:
        return resolve_planner_start_minutes(selected_date, period, local=local, raw_start=raw_start)
    except StartTimeValidationError as exc:
        raise ValidationError(str(exc)) from exc


@api_view(["GET"])
def route_forecast_view(request, slug: str):
    route = get_route(slug)
    selected, period, access = _resolve_date_period(request)
    if access.status_for(selected) != "available":
        return _forecast_access_denied(access, selected)
    local = now_tehran()
    speed = parse_speed(request.query_params.get("speed"))
    start = _resolve_start_minutes(request, selected, period, local)
    return _private_forecast(
        route_forecast(
            route,
            selected_date=selected,
            period=period,
            start_minutes=start,
            speed=speed,
        ),
        access,
    )


@api_view(["GET"])
def point_forecast_view(request, slug: str):
    weather_point = get_weather_point(slug)
    selected, period, access = _resolve_date_period(request)
    if access.status_for(selected) != "available":
        return _forecast_access_denied(access, selected)
    return _private_forecast(point_forecast(weather_point, selected_date=selected, period=period), access)


@api_view(["GET"])
def search_suggestions_view(request):
    query = request.query_params.get("q", "")
    results = search_suggestions(query=query)
    return Response(
        {
            "query": query,
            "results": results,
            "empty": not results,
            "meta": meta_base(selected_date=now_tehran().date(), period="morning"),
        }
    )


@api_view(["GET"])
def robots_txt(_request):
    from django.conf import settings

    body = (
        "User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /admin/\n"
        f"Sitemap: {settings.PUBLIC_SITE_ORIGIN}/sitemap.xml\n"
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


@api_view(["GET"])
def sitemap_xml(_request):
    from django.utils.html import escape

    from django.conf import settings

    base = settings.PUBLIC_SITE_ORIGIN
    successful_forecast_statuses = (
        ForecastSnapshot.Status.SUCCESS,
        ForecastSnapshot.Status.PARTIAL,
    )

    # ForecastRecord.generated_at is written only when normalized hourly data
    # is persisted for a point.  Looking at records (rather than an ingest
    # attempt or the latest global snapshot) means a failed/empty point batch
    # cannot move its sitemap timestamp.
    point_forecast_lastmod = (
        ForecastRecord.objects.filter(
            weather_point_id=OuterRef("pk"),
            data_mode="live",
            provider="open-meteo",
            snapshot__status__in=successful_forecast_statuses,
        )
        .order_by("-generated_at", "-pk")
        .values("generated_at")[:1]
    )
    point_rows = list(
        publicly_visible_weather_points()
        .filter(seo_indexable=True)
        .annotate(forecast_updated_at=Subquery(point_forecast_lastmod))
        .order_by("slug")
        .values("slug", "updated_at", "forecast_updated_at")
    )
    route_forecast_lastmod = (
        ForecastRecord.objects.filter(
            weather_point__route_links__route_id=OuterRef("pk"),
            data_mode="live",
            provider="open-meteo",
            snapshot__status__in=successful_forecast_statuses,
        )
        .order_by("-generated_at", "-pk")
        .values("generated_at")[:1]
    )
    route_rows = list(
        Route.objects.filter(is_active=True)
        .annotate(points_updated_at=Max("points__weather_point__updated_at"))
        .annotate(forecast_updated_at=Subquery(route_forecast_lastmod))
        .order_by("slug")
        .values("slug", "updated_at", "points_updated_at", "forecast_updated_at")
    )
    # The destinations hub renders catalog identity/order only; forecast
    # refreshes must not make this URL look changed.  Include retired primary
    # rows because sync keeps them as tombstones and timestamps their
    # deactivation, so removing a destination is observable.
    destination_rows = destination_catalog_timestamp_points().values("updated_at")

    def latest_timestamp(*values):
        available = [value for value in values if value is not None]
        return max(available) if available else None

    destination_lastmod = latest_timestamp(*(row["updated_at"] for row in destination_rows))

    def entry(url: str, updated_at=None) -> str:
        lastmod = (
            f"<lastmod>{updated_at.astimezone(dt_timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')}</lastmod>"
            if updated_at is not None
            else ""
        )
        return f"<url><loc>{escape(url)}</loc>{lastmod}</url>"

    urls = [
        entry(f"{base}/"),
        entry(f"{base}/destinations", destination_lastmod),
        *(
            entry(
                f"{base}/points/{row['slug']}",
                latest_timestamp(row["updated_at"], row["forecast_updated_at"]),
            )
            for row in point_rows
        ),
        *(
            entry(
                f"{base}/routes/{row['slug']}",
                latest_timestamp(
                    row["updated_at"],
                    row["points_updated_at"],
                    row["forecast_updated_at"],
                ),
            )
            for row in route_rows
        ),
    ]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml.extend(urls)
    xml.append("</urlset>")
    response = HttpResponse("".join(xml), content_type="application/xml; charset=utf-8")
    # Keep CDN storage possible, but require revalidation so a successful
    # forecast write cannot leave an old lastmod cached for a full day.
    response["Cache-Control"] = "public, no-cache, must-revalidate"
    return response

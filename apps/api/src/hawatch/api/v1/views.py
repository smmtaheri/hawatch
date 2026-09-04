from __future__ import annotations

from datetime import timedelta

from django.db import connection
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
from hawatch.modules.catalog.runtime import publicly_visible_weather_points
from hawatch.modules.catalog.seed import refresh_if_bucket_changed
from hawatch.modules.forecasts.models import ForecastSnapshot, ForecastRecord, WeatherPoint
from hawatch.modules.routes.models import Route
from hawatch.integrations.weather.ingest import snapshot_freshness


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
    return selected, period


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
    selected, period = _resolve_date_period(request)
    local = now_tehran()
    speed = parse_speed(request.query_params.get("speed"))
    start = _resolve_start_minutes(request, selected, period, local)
    return Response(
        route_forecast(
            route,
            selected_date=selected,
            period=period,
            start_minutes=start,
            speed=speed,
        )
    )


@api_view(["GET"])
def point_forecast_view(request, slug: str):
    weather_point = get_weather_point(slug)
    selected, period = _resolve_date_period(request)
    return Response(point_forecast(weather_point, selected_date=selected, period=period))


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
    body = "User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /admin/\nSitemap: /sitemap.xml\n"
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


@api_view(["GET"])
def sitemap_xml(_request):
    from django.utils.html import escape

    from django.conf import settings

    base = settings.PUBLIC_SITE_ORIGIN
    points = publicly_visible_weather_points().order_by("slug").values_list("slug", flat=True)
    routes = Route.objects.filter(is_active=True).values_list("slug", flat=True)
    urls = [f"{base}/"] + [f"{base}/points/{slug}" for slug in points] + [f"{base}/routes/{slug}" for slug in routes]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml.extend(f"<url><loc>{escape(url)}</loc></url>" for url in urls)
    xml.append("</urlset>")
    return HttpResponse("".join(xml), content_type="application/xml; charset=utf-8")

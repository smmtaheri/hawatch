from __future__ import annotations

from datetime import timedelta

from django.db import connection
from django.utils import timezone as dj_timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from hawatch.api.v1.serializers import (
    destination_forecast,
    get_destination,
    get_route,
    list_destinations,
    meta_base,
    route_forecast,
    serialize_destination,
    serialize_route,
)
from hawatch.common.time import now_tehran, parse_date, parse_period, parse_speed, parse_start_minutes
from hawatch.common.observability import metrics_authorized, metrics_view, set_health
from hawatch.modules.catalog.seed import refresh_if_bucket_changed
from hawatch.modules.destinations.models import Destination
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
            "destinations": Destination.objects.filter(is_active=True).count(),
            "routes": Route.objects.filter(destination__is_active=True).count(),
            "weather_points": WeatherPoint.objects.filter(destination__is_active=True).count(),
        }
        forecast = {
            "provider": "open-meteo",
            "freshness": freshness,
            "latest_attempt_status": latest_attempt.status if latest_attempt else None,
            "latest_attempt_at": latest_attempt.generated_at.isoformat() if latest_attempt else None,
            "latest_usable_at": latest_usable.generated_at.isoformat() if latest_usable else None,
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
def destinations_list(request):
    refresh_if_bucket_changed()
    query = request.query_params.get("query", "")
    items = list_destinations(query=query)
    today = now_tehran().date()
    return Response(
        {
            "results": [serialize_destination(item) for item in items],
            "empty": not items,
            "query": query,
            "meta": meta_base(selected_date=today, period="morning"),
        }
    )


@api_view(["GET"])
def destination_detail(request, slug: str):
    refresh_if_bucket_changed()
    destination = get_destination(slug)
    today = now_tehran().date()
    return Response(
        {
            "destination": serialize_destination(destination, include_routes=True),
            "meta": meta_base(selected_date=today, period="morning"),
        }
    )


@api_view(["GET"])
def destination_forecast_view(request, slug: str):
    destination = get_destination(slug)
    today = now_tehran().date()
    selected = parse_date(request.query_params.get("date"), today)
    period = parse_period(request.query_params.get("period"))
    return Response(destination_forecast(destination, selected_date=selected, period=period))


@api_view(["GET"])
def route_detail(request, slug: str):
    refresh_if_bucket_changed()
    route = get_route(slug)
    today = now_tehran().date()
    return Response({"route": serialize_route(route), "meta": meta_base(selected_date=today, period="morning")})


@api_view(["GET"])
def route_forecast_view(request, slug: str):
    route = get_route(slug)
    today = now_tehran().date()
    selected = parse_date(request.query_params.get("date"), today)
    period = parse_period(request.query_params.get("period"))
    speed = parse_speed(request.query_params.get("speed"))
    start = parse_start_minutes(
        request.query_params.get("start_time"),
        period,
        route.default_start_minutes,
    )
    return Response(
        route_forecast(
            route,
            selected_date=selected,
            period=period,
            start_minutes=start,
            speed=speed,
        )
    )

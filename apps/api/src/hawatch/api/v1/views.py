from __future__ import annotations

from django.db import connection
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
from hawatch.common.observability import metrics_view, set_health
from hawatch.modules.catalog.seed import refresh_if_bucket_changed


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

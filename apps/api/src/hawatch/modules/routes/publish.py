"""Shared route normalization and publish helpers for Admin and catalog import."""

from __future__ import annotations

from django.db import transaction
from django.db.models import F, Max

from hawatch.modules.catalog.search import rebuild_search_index
from hawatch.modules.routes.models import Route, RoutePoint
from hawatch.modules.routes.timing import route_timing_complete


def axis_for_index(index: int, total: int) -> tuple[int, int]:
    if total <= 1:
        return 50, 50
    x = 12 + round((76 * index) / (total - 1))
    y = 72 - round((44 * index) / (total - 1))
    return x, y


def shift_route_point_sort_orders(route: Route) -> None:
    """Move a route's orders above their current maximum without collisions.

    A fixed ``+1000`` offset can collide with an existing stale point already
    at that temporary value (for example while importing a changed fixture).
    Moving every value above the current maximum is safe for the unique
    ``(route, sort_order)`` constraint and is used only as a short-lived
    intermediate state before dense ordering is written.
    """
    maximum = RoutePoint.objects.filter(route=route).aggregate(maximum=Max("sort_order"))["maximum"]
    if maximum is None:
        return
    RoutePoint.objects.filter(route=route).update(sort_order=F("sort_order") + int(maximum) + 1)


def schedule_search_index_rebuild() -> None:
    transaction.on_commit(rebuild_search_index)


def synchronize_route_point_from_weather_point(point: RoutePoint) -> list[str]:
    """Copy denormalized display fields from the linked WeatherPoint when present."""
    updated: list[str] = []
    wp = point.weather_point
    if wp is None:
        return updated
    if point.name != wp.name:
        point.name = wp.name
        updated.append("name")
    if point.elevation_m != wp.elevation_m:
        point.elevation_m = wp.elevation_m
        updated.append("elevation_m")
    if wp.location is not None and point.location != wp.location:
        point.location = wp.location
        updated.append("location")
    return updated


def normalize_and_publish_route(route: Route, *, rebuild_search: bool = True) -> Route:
    """Normalize ordered RoutePoints and demote incomplete timing to pending.

    Used by Django Admin and catalog import so both paths produce the same
    denormalized timeline fields without a deploy or fixture edit.
    """
    points = list(route.points.select_related("weather_point").order_by("sort_order", "pk"))
    total = len(points)

    # Temporarily shift sort_order to avoid UniqueConstraint collisions while renumbering.
    if points:
        shift_route_point_sort_orders(route)
        points = list(route.points.select_related("weather_point").order_by("sort_order", "pk"))

    # Re-number sort_order densely and deterministically.
    for index, point in enumerate(points):
        desired_order = index + 1
        fields = synchronize_route_point_from_weather_point(point)
        point.sort_order = desired_order
        fields.append("sort_order")
        axis_x, axis_y = axis_for_index(index, total)
        if point.axis_x != axis_x:
            point.axis_x = axis_x
            fields.append("axis_x")
        if point.axis_y != axis_y:
            point.axis_y = axis_y
            fields.append("axis_y")

        previous_cumulative = 0 if index == 0 else points[index - 1].cumulative_minutes
        if point.cumulative_minutes is not None and previous_cumulative is not None:
            segment = int(point.cumulative_minutes) - int(previous_cumulative)
            if index == 0:
                segment = 0
            if point.segment_minutes != segment:
                point.segment_minutes = segment
                fields.append("segment_minutes")
            # Keep legacy base_minutes aligned with cumulative when present.
            if point.base_minutes != point.cumulative_minutes:
                point.base_minutes = point.cumulative_minutes
                fields.append("base_minutes")

        if route.one_way_minutes and point.cumulative_minutes is not None:
            progress = round((int(point.cumulative_minutes) / int(route.one_way_minutes)) * 100, 2)
            if point.progress_pct != progress:
                point.progress_pct = progress
                fields.append("progress_pct")
        elif point.progress_pct is not None:
            point.progress_pct = None
            fields.append("progress_pct")

        if fields:
            point.save(update_fields=sorted(set(fields)))

    origin = points[0].weather_point if points else None
    target = points[-1].weather_point if points else None
    route_fields: list[str] = []
    if origin is not None and route.origin_weather_point_id != origin.id:
        route.origin_weather_point = origin
        route_fields.append("origin_weather_point")
        if origin.location is not None and route.origin_location != origin.location:
            route.origin_location = origin.location
            route_fields.append("origin_location")
    if target is not None and route.target_weather_point_id != target.id:
        route.target_weather_point = target
        route_fields.append("target_weather_point")

    complete = route_timing_complete(
        timing_status=route.timing_status,
        one_way_minutes=route.one_way_minutes,
        points=points,
    )
    if route.timing_status in {Route.TimingStatus.ESTIMATED, Route.TimingStatus.CURATED} and not complete:
        route.timing_status = Route.TimingStatus.PENDING
        route_fields.append("timing_status")
        for point in points:
            if point.timing_status != RoutePoint.TimingStatus.PENDING:
                point.timing_status = RoutePoint.TimingStatus.PENDING
                point.save(update_fields=["timing_status"])

    if route_fields:
        route.save(update_fields=sorted(set(route_fields + ["updated_at"])))

    if rebuild_search:
        schedule_search_index_rebuild()
    return route

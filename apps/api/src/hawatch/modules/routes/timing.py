"""Shared route timing usability checks (no base_minutes evidence)."""

from __future__ import annotations

import math
from typing import Any, Iterable


USABLE_TIMING_STATUSES = frozenset({"estimated", "curated"})


def ordered_route_points(points: Iterable[Any]) -> list[Any]:
    """Return points ordered by sort_order when available."""
    items = list(points)
    if items and hasattr(items[0], "sort_order"):
        return sorted(items, key=lambda point: point.sort_order)
    return items


def route_mean_elevation_m(points: Iterable[Any]) -> float | None:
    """Estimate route mean elevation from ordered, cataloged route checkpoints.

    Elevation is linearly interpolated between adjacent checkpoints and weighted
    by their recorded segment distance. If that distance is missing, straight-
    line distance between checkpoint locations is used; the estimate is not a
    substitute for a full DEM/GPX elevation profile.
    """

    ordered = ordered_route_points(points)
    elevations: list[float | None] = []
    coordinates: list[tuple[float, float] | None] = []
    for point in ordered:
        elevation = getattr(point, "effective_elevation_m", None)
        if elevation is None:
            elevation = getattr(point, "elevation_m", None)
        try:
            elevations.append(float(elevation) if elevation is not None else None)
        except (TypeError, ValueError):
            elevations.append(None)

        location = getattr(point, "effective_location", None)
        if location is None:
            location = getattr(point, "location", None)
        try:
            coordinates.append((float(location.y), float(location.x)))
        except (AttributeError, TypeError, ValueError):
            coordinates.append(None)

    weighted_elevation = 0.0
    total_distance = 0.0
    for index in range(1, len(ordered)):
        start_elevation = elevations[index - 1]
        end_elevation = elevations[index]
        if start_elevation is None or end_elevation is None:
            continue

        distance = getattr(ordered[index], "segment_distance_m", None)
        try:
            distance = float(distance) if distance is not None else 0.0
        except (TypeError, ValueError):
            distance = 0.0
        if distance <= 0:
            start_coordinates = coordinates[index - 1]
            end_coordinates = coordinates[index]
            if start_coordinates is not None and end_coordinates is not None:
                lat1, lon1 = map(math.radians, start_coordinates)
                lat2, lon2 = map(math.radians, end_coordinates)
                delta_lat = lat2 - lat1
                delta_lon = lon2 - lon1
                haversine = (
                    math.sin(delta_lat / 2) ** 2
                    + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
                )
                distance = 2 * 6_371_000 * math.asin(math.sqrt(min(1.0, haversine)))
        if distance <= 0:
            distance = 1.0

        weighted_elevation += ((start_elevation + end_elevation) / 2) * distance
        total_distance += distance

    if total_distance > 0:
        return weighted_elevation / total_distance
    known_elevations = [elevation for elevation in elevations if elevation is not None]
    return sum(known_elevations) / len(known_elevations) if known_elevations else None


def route_timing_complete(*, timing_status: str, one_way_minutes: int | None, points: Iterable[Any]) -> bool:
    """Return True when route timing is complete and internally consistent.

    Rules:
    - route status is estimated or curated
    - one_way_minutes is present and positive
    - at least two ordered RoutePoints
    - every RoutePoint status is estimated or curated
    - every RoutePoint has cumulative_minutes
    - first cumulative is exactly 0
    - cumulatives are strictly increasing
    - final cumulative equals one_way_minutes

    Legacy base_minutes is never treated as timing evidence.
    """
    if timing_status not in USABLE_TIMING_STATUSES:
        return False
    if one_way_minutes is None or int(one_way_minutes) <= 0:
        return False
    ordered = ordered_route_points(points)
    if len(ordered) < 2:
        return False

    cumulatives: list[int] = []
    for point in ordered:
        status = getattr(point, "timing_status", None)
        if status not in USABLE_TIMING_STATUSES:
            return False
        cumulative = getattr(point, "cumulative_minutes", None)
        if cumulative is None:
            return False
        cumulatives.append(int(cumulative))

    if cumulatives[0] != 0:
        return False
    for previous, current in zip(cumulatives, cumulatives[1:]):
        if current <= previous:
            return False
    if cumulatives[-1] != int(one_way_minutes):
        return False
    return True

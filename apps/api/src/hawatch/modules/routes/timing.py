"""Shared route timing usability checks (no base_minutes evidence)."""

from __future__ import annotations

from typing import Any, Iterable


USABLE_TIMING_STATUSES = frozenset({"estimated", "curated"})


def ordered_route_points(points: Iterable[Any]) -> list[Any]:
    """Return points ordered by sort_order when available."""
    items = list(points)
    if items and hasattr(items[0], "sort_order"):
        return sorted(items, key=lambda point: point.sort_order)
    return items


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

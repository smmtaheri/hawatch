"""Canonical database relationships used by public SSR link builders.

Keeping the relationship query outside the template view prevents the SEO
validator and the HTML renderer from drifting apart.  It deliberately uses
only explicit RoutePoint/endpoint links (plus the documented target-label
fallback for a physical endpoint such as a lake shore).
"""

from __future__ import annotations

from django.db.models import Q, QuerySet

from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route


def related_public_routes(point: WeatherPoint) -> QuerySet[Route]:
    """Return active routes that explicitly reference ``point``.

    A primary destination may also be the canonical label for a physical
    endpoint represented by another RoutePoint.  Matching the exact catalog
    name/page name preserves that existing, curated relationship without
    guessing from slugs or geographic proximity.
    """

    relation = (
        Q(points__weather_point=point)
        | Q(origin_weather_point=point)
        | Q(target_weather_point=point)
    )
    if point.kind == WeatherPoint.Kind.PRIMARY:
        relation |= Q(target_label=point.name) | Q(target_label=point.page_name)
    return (
        Route.objects.filter(relation, is_active=True)
        .distinct()
        .order_by("sort_order", "slug")
    )

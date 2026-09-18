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
from hawatch.modules.catalog.runtime import publicly_visible_destinations


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


def related_public_destinations(point: WeatherPoint) -> QuerySet[WeatherPoint]:
    """Return destination siblings that provide an SSR entry for a village.

    A point-only village is stored in the same versioned catalog as the
    independent destination it serves (for example a mountain or forest).
    That catalog grouping is the source of truth for this relationship; no
    slug list or geographic guess is maintained in the renderer. Restricting
    the result to non-village destinations prevents one access village from
    becoming the parent of another village when a catalog contains several
    access settlements.
    """

    if point.place_type != "village" or not point.catalog_version:
        return WeatherPoint.objects.none()
    return (
        publicly_visible_destinations()
        .filter(catalog_version=point.catalog_version)
        .exclude(pk=point.pk)
        .exclude(place_type="village")
        .order_by("-is_popular", "popular_order", "page_name", "slug")
    )


def related_public_villages(destination: WeatherPoint) -> QuerySet[WeatherPoint]:
    """Return indexable villages that should receive a link from a destination.

    The inverse of :func:`related_public_destinations` is kept as a separate
    query so the destination page itself provides the required crawlable
    inbound link.  Both directions use the same catalog-version grouping.
    """

    if destination.place_type == "village" or not destination.catalog_version:
        return WeatherPoint.objects.none()
    return (
        publicly_visible_destinations()
        .filter(catalog_version=destination.catalog_version, place_type="village")
        .order_by("page_name", "slug")
    )

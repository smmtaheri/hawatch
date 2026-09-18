"""Canonical database relationships used by public SSR link builders.

Keeping the relationship query outside the template view prevents the SEO
validator and the HTML renderer from drifting apart.  It deliberately uses
only explicit RoutePoint/endpoint links (plus the documented target-label
fallback for a physical endpoint such as a lake shore).
"""

from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt

from django.db.models import Q, QuerySet

from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route
from hawatch.modules.catalog.identity import ACCESS_PLACE_TYPES
from hawatch.modules.catalog.runtime import publicly_visible_destinations, publicly_visible_weather_points


MAX_SIMILAR_DESTINATIONS = 4

# These are curator-approved relationships for the first category where the
# product already has several genuinely interchangeable destinations.  The
# resolver keeps this layer ahead of its deterministic fallback, so an
# operator can correct a merely geographic match without adding a database
# relation or changing forecast data.  New entries are optional: category,
# place type, catalog grouping and distance still provide safe discovery.
CURATED_SIMILAR_DESTINATION_SLUGS: dict[str, tuple[str, ...]] = {
    "dizin-ski-resort": ("darbandsar-ski-resort", "tochal-ski-resort", "abali-ski-resort", "sabalan-alvares-ski-resort"),
    "darbandsar-ski-resort": ("dizin-ski-resort", "tochal-ski-resort", "abali-ski-resort", "sabalan-alvares-ski-resort"),
    "tochal-ski-resort": ("darbandsar-ski-resort", "dizin-ski-resort", "abali-ski-resort", "sabalan-alvares-ski-resort"),
    "abali-ski-resort": ("tochal-ski-resort", "darbandsar-ski-resort", "dizin-ski-resort", "sabalan-alvares-ski-resort"),
    "sabalan-alvares-ski-resort": ("dizin-ski-resort", "darbandsar-ski-resort", "tochal-ski-resort", "abali-ski-resort"),
}


def _point_distance_km(first: WeatherPoint, second: WeatherPoint) -> float:
    """Return a stable, display-independent distance for candidate ranking."""

    if not first.location or not second.location:
        return float("inf")
    lat1, lon1 = radians(float(first.location.y)), radians(float(first.location.x))
    lat2, lon2 = radians(float(second.location.y)), radians(float(second.location.x))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * atan2(sqrt(value), sqrt(max(0.0, 1 - value)))


def similar_destinations_title(point: WeatherPoint) -> str:
    """Return concise, user-facing copy for the point's discovery group."""

    category = str(point.category_key or "").strip().casefold()
    place_type = str(point.place_type or "").strip().casefold()
    if category == "ski":
        return "مقصدهای مشابه"
    if place_type == "neighborhood":
        return "محله‌های مشابه"
    if place_type == "city":
        return "شهرهای نزدیک و مشابه"
    if place_type == "village":
        return "روستاهای نزدیک"
    if category in {"mountain", "ridge", "volcano"} or place_type in {"summit", "ridge"}:
        return "قله‌ها و ارتفاعات مشابه"
    if category == "waterfall" or place_type == "waterfall":
        return "آبشارهای مشابه"
    if category == "lake" or place_type == "lake":
        return "دریاچه‌های مشابه"
    if category == "desert" or place_type == "desert":
        return "کویرهای مشابه"
    if category == "forest" or place_type == "forest":
        return "جنگل‌های مشابه"
    return "مقصدهای مشابه"


def related_public_similar_destinations(
    point: WeatherPoint,
    *,
    limit: int = MAX_SIMILAR_DESTINATIONS,
) -> list[WeatherPoint]:
    """Return up to four stable, crawlable alternatives for a point-only page.

    Curated relationships are returned first.  The fallback only considers
    indexable public points with the same semantic category/place type, or an
    exact catalog grouping for access settlements, and then ranks by region,
    distance and the existing destination order.  Forecast timestamps never
    participate, so links remain stable between weather runs.
    """

    limit = max(0, min(int(limit), MAX_SIMILAR_DESTINATIONS))
    if not limit:
        return []

    candidates = list(
        publicly_visible_destinations()
        .exclude(pk=point.pk)
        .only(
            "id",
            "slug",
            "name",
            "page_name",
            "short_label",
            "short_category",
            "category",
            "place_type",
            "category_key",
            "region",
            "catalog_version",
            "elevation_m",
            "location",
            "kind",
            "popular_order",
            "is_popular",
        )
    )
    by_slug = {candidate.slug: candidate for candidate in candidates}
    selected: list[WeatherPoint] = []
    selected_ids: set[int] = set()

    def add(candidate: WeatherPoint | None) -> None:
        if candidate is None or candidate.pk in selected_ids or len(selected) >= limit:
            return
        selected.append(candidate)
        selected_ids.add(candidate.pk)

    for slug in CURATED_SIMILAR_DESTINATION_SLUGS.get(point.slug, ()):
        add(by_slug.get(slug))

    category = str(point.category_key or "").strip().casefold()
    place_type = str(point.place_type or "").strip().casefold()
    region = str(point.region or "").strip().casefold()
    catalog_version = str(point.catalog_version or "").strip()

    def rank(candidate: WeatherPoint) -> tuple[int, int, int, float, int, str]:
        candidate_category = str(candidate.category_key or "").strip().casefold()
        candidate_type = str(candidate.place_type or "").strip().casefold()
        same_catalog = bool(catalog_version and candidate.catalog_version == catalog_version)
        same_region = bool(region and candidate.region and candidate.region.strip().casefold() == region)
        same_category = bool(category and candidate_category == category)
        same_type = bool(place_type and candidate_type == place_type)
        # Exact catalog grouping is the strongest inferred relationship for an
        # access settlement; otherwise semantic category is the primary key.
        group_rank = 0 if same_catalog and place_type in ACCESS_PLACE_TYPES and candidate.kind == WeatherPoint.Kind.PRIMARY else 1
        semantic_rank = 0 if same_category else 1 if same_type else 2
        region_rank = 0 if same_region else 1
        return (
            group_rank,
            semantic_rank,
            region_rank,
            _point_distance_km(point, candidate),
            0 if candidate.is_popular else 1,
            f"{candidate.page_name or candidate.name}|{candidate.slug}",
        )

    inferred = sorted(
        (
            candidate
            for candidate in candidates
            if candidate.pk not in selected_ids
            and (
                (catalog_version and candidate.catalog_version == catalog_version and place_type in ACCESS_PLACE_TYPES and candidate.kind == WeatherPoint.Kind.PRIMARY)
                or (category and candidate.category_key and str(candidate.category_key).strip().casefold() == category)
                or (
                    not category
                    and place_type
                    and candidate.place_type
                    and str(candidate.place_type).strip().casefold() == place_type
                )
            )
        ),
        key=rank,
    )
    for candidate in inferred:
        add(candidate)
    return selected


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
    """Return destination siblings that provide an SSR entry for an access settlement.

    A point-only city, village, or neighborhood is stored in the same versioned catalog as the
    independent destination it serves (for example a mountain or forest).
    That catalog grouping is the source of truth for this relationship; no
    slug list or geographic guess is maintained in the renderer. Restricting
    the result to non-access destinations prevents one access settlement from
    becoming the parent of another access settlement when a catalog contains several
    access settlements.
    """

    if point.place_type not in ACCESS_PLACE_TYPES or not point.catalog_version:
        return WeatherPoint.objects.none()
    return (
        publicly_visible_destinations()
        .filter(catalog_version=point.catalog_version)
        .exclude(pk=point.pk)
        .exclude(place_type__in=ACCESS_PLACE_TYPES)
        .order_by("-is_popular", "popular_order", "page_name", "slug")
    )


def related_public_villages(destination: WeatherPoint) -> QuerySet[WeatherPoint]:
    """Return indexable cities, villages, and neighborhoods linked from a destination.

    The inverse of :func:`related_public_destinations` is kept as a separate
    query so the destination page itself provides the required crawlable
    inbound link.  Both directions use the same catalog-version grouping.
    """

    if destination.place_type in ACCESS_PLACE_TYPES or not destination.catalog_version:
        return WeatherPoint.objects.none()
    return (
        publicly_visible_destinations()
        .filter(catalog_version=destination.catalog_version, place_type__in=ACCESS_PLACE_TYPES)
        .order_by("page_name", "slug")
    )

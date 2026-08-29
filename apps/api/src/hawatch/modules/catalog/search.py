from __future__ import annotations

import re

from django.db import transaction
from django.db.models import Q

from hawatch.modules.catalog.models import SearchIndexEntry
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import WeatherPoint

_ZWNJ = "\u200c"
_ARABIC_Y = "ي"
_PERSIAN_Y = "ی"
_ARABIC_K = "ك"
_PERSIAN_K = "ک"


def normalize_search_text(value: str) -> str:
    text = value.strip().replace(_ARABIC_Y, _PERSIAN_Y).replace(_ARABIC_K, _PERSIAN_K)
    text = text.replace(_ZWNJ, "")
    text = re.sub(r"\s+", "", text)
    return text.casefold()


def _destination_entries(destination: Destination) -> list[SearchIndexEntry]:
    rows: list[SearchIndexEntry] = []
    terms: list[tuple[str, SearchIndexEntry.MatchKind, int]] = [
        (destination.name, SearchIndexEntry.MatchKind.NAME, 0),
        (destination.tile_name, SearchIndexEntry.MatchKind.ALIAS, 1),
    ]
    for alias in destination.aliases or []:
        terms.append((alias, SearchIndexEntry.MatchKind.ALIAS, 1))
    seen: set[str] = set()
    for label, match_kind, rank in terms:
        normalized = normalize_search_text(label)
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        rows.append(
            SearchIndexEntry(
                kind=SearchIndexEntry.Kind.DESTINATION,
                match_kind=match_kind,
                normalized_term=normalized,
                display_label=destination.name,
                display_hint="مقصد",
                destination_slug=destination.slug,
                weather_point_slug="",
                rank=rank,
                is_active=True,
            )
        )
    return rows


def _point_entries(point: WeatherPoint) -> list[SearchIndexEntry]:
    if point.slug.startswith("dest:"):
        return []
    # DestinationProfile weather points are indexed only as destinations.
    if Destination.objects.filter(weather_point_id=point.id).exists():
        return []
    destination = (
        Destination.objects.filter(routes__points__weather_point=point, is_active=True)
        .order_by("popular_order", "slug")
        .first()
    )
    if destination is None and point.destination_id and point.destination.is_active:
        destination = point.destination
    if destination is None or not destination.is_active:
        return []
    hint = f"نقطهٔ مسیر · {destination.tile_name}"
    rows: list[SearchIndexEntry] = []
    terms: list[tuple[str, SearchIndexEntry.MatchKind, int]] = [
        (point.name, SearchIndexEntry.MatchKind.NAME, 0),
    ]
    for alias in point.aliases or []:
        terms.append((alias, SearchIndexEntry.MatchKind.ALIAS, 1))
    seen: set[str] = set()
    for label, match_kind, rank in terms:
        normalized = normalize_search_text(label)
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        rows.append(
            SearchIndexEntry(
                kind=SearchIndexEntry.Kind.POINT,
                match_kind=match_kind,
                normalized_term=normalized,
                display_label=point.name,
                display_hint=hint,
                destination_slug=destination.slug,
                weather_point_slug=point.slug,
                rank=rank,
                is_active=True,
            )
        )
    return rows


@transaction.atomic
def rebuild_search_index() -> dict[str, int]:
    SearchIndexEntry.objects.all().delete()
    rows: list[SearchIndexEntry] = []
    for destination in Destination.objects.filter(is_active=True):
        rows.extend(_destination_entries(destination))
    point_qs = (
        WeatherPoint.objects.exclude(slug__startswith="dest:")
        .filter(
            Q(destination__is_active=True)
            | Q(route_links__route__destination__is_active=True)
            | Q(destination_profile__is_active=True)
        )
        .select_related("destination")
        .distinct()
    )
    for point in point_qs:
        rows.extend(_point_entries(point))
    if rows:
        SearchIndexEntry.objects.bulk_create(rows, batch_size=500)
    return {"entries": len(rows)}


def search_suggestions(*, query: str, limit: int = 8) -> list[dict]:
    normalized = normalize_search_text(query)
    if len(normalized) < 2:
        return []
    matches = list(
        SearchIndexEntry.objects.filter(is_active=True, normalized_term__startswith=normalized).order_by(
            "rank", "kind", "display_label"
        )[: limit * 3]
    )
    results: list[dict] = []
    seen_keys: set[str] = set()
    for row in matches:
        key = f"{row.kind}:{row.destination_slug}:{row.weather_point_slug}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        if row.kind == SearchIndexEntry.Kind.DESTINATION:
            href = f"/destination/{row.destination_slug}"
            result_type = "destination"
            slug = row.destination_slug
        else:
            href = f"/points/{row.weather_point_slug}"
            result_type = "point"
            slug = row.weather_point_slug
        results.append(
            {
                "type": result_type,
                "slug": slug,
                "label": row.display_label,
                "hint": row.display_hint,
                "href": href,
                "match_kind": row.match_kind,
            }
        )
        if len(results) >= limit:
            break
    return results

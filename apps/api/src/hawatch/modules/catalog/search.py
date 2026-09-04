from __future__ import annotations

import re

from django.db import transaction
from django.db.models import Case, IntegerField, Value, When

from hawatch.modules.catalog.models import SearchIndexEntry
from hawatch.modules.forecasts.models import WeatherPoint

_ZWNJ = "\u200c"


def normalize_search_text(value: str) -> str:
    text = str(value or "").strip().replace("ي", "ی").replace("ك", "ک")
    text = text.replace(_ZWNJ, "")
    return re.sub(r"\s+", "", text).casefold()


def _point_entries(point: WeatherPoint) -> list[SearchIndexEntry]:
    if not point.is_active or point.slug.startswith(("dest:", "route:")):
        return []
    terms = [(point.name, SearchIndexEntry.MatchKind.NAME, 0)]
    if point.page_name and point.page_name != point.name:
        terms.append((point.page_name, SearchIndexEntry.MatchKind.ALIAS, 1))
    terms.extend((alias, SearchIndexEntry.MatchKind.ALIAS, 1) for alias in point.aliases or [])
    rows: list[SearchIndexEntry] = []
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
                display_label=point.page_name or point.name,
                display_hint="نقطهٔ شاخص" if point.importance == "primary" else "نقطهٔ مسیر",
                weather_point_slug=point.slug,
                rank=rank if point.importance != "primary" else max(0, rank - 1),
                is_active=True,
            )
        )
    return rows


@transaction.atomic
def rebuild_search_index() -> dict[str, int]:
    SearchIndexEntry.objects.all().delete()
    rows: list[SearchIndexEntry] = []
    for point in WeatherPoint.objects.filter(is_active=True).order_by("importance", "popular_order", "slug"):
        rows.extend(_point_entries(point))
    if rows:
        SearchIndexEntry.objects.bulk_create(rows, batch_size=500)
    return {"entries": len(rows)}


def search_suggestions(*, query: str, limit: int = 8) -> list[dict]:
    normalized = normalize_search_text(query)
    if len(normalized) < 2:
        return []
    matches = list(
        SearchIndexEntry.objects.filter(is_active=True, normalized_term__contains=normalized)
        .annotate(
            match_position=Case(
                When(normalized_term=normalized, then=Value(0)),
                When(normalized_term__startswith=normalized, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("match_position", "rank", "display_label", "id")[: limit * 3]
    )
    results: list[dict] = []
    seen: set[str] = set()
    for row in matches:
        slug = row.weather_point_slug
        if not slug or slug in seen:
            continue
        seen.add(slug)
        results.append(
            {
                "type": "point",
                "slug": slug,
                "label": row.display_label,
                "hint": row.display_hint,
                "href": f"/points/{slug}",
                "match_kind": row.match_kind,
            }
        )
        if len(results) >= limit:
            break
    return results

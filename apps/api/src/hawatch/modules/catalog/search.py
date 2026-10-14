from __future__ import annotations

from django.db import transaction

from hawatch.modules.catalog.models import SearchIndexEntry
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.catalog.search_text import SearchQuery, normalize_search_text, point_search_terms


def _point_entries(point: WeatherPoint) -> list[SearchIndexEntry]:
    if not point.is_active or point.slug.startswith(("dest:", "route:")):
        return []
    terms = point_search_terms(point)
    rows: list[SearchIndexEntry] = []
    seen: set[str] = set()
    for index, label in enumerate(terms):
        normalized = normalize_search_text(label)
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        rows.append(
            SearchIndexEntry(
                kind=SearchIndexEntry.Kind.POINT,
                match_kind=SearchIndexEntry.MatchKind.NAME if index == 0 else SearchIndexEntry.MatchKind.ALIAS,
                normalized_term=normalized,
                display_label=point.page_name or point.name,
                display_hint="نقطهٔ شاخص" if point.importance == "primary" else "نقطهٔ مسیر",
                weather_point_slug=point.slug,
                rank=0 if point.importance == "primary" else 1,
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
    from hawatch.modules.catalog.search_payload import invalidate_search_index_payload

    transaction.on_commit(invalidate_search_index_payload)
    return {"entries": len(rows)}


def search_suggestions(*, query: str, limit: int = 8) -> list[dict]:
    parsed = SearchQuery.parse(query)
    if len(parsed.compact) < 2 or len(parsed.compact) > 160:
        return []
    # Every match contains the longest query token in at least one term.
    # Fetch that small set of points, then score all their aliases together.
    candidates = SearchIndexEntry.objects.filter(
        is_active=True,
        normalized_term__contains=max(parsed.tokens, key=len),
    ).values("weather_point_slug")
    grouped: dict[str, list[SearchIndexEntry]] = {}
    for row in SearchIndexEntry.objects.filter(weather_point_slug__in=candidates, is_active=True).order_by("id"):
        grouped.setdefault(row.weather_point_slug, []).append(row)
    matches = []
    for rows in grouped.values():
        score = parsed.score([row.normalized_term for row in rows])
        if score is not None:
            matches.append((score[0], rows[score[1]]))
    matches.sort(key=lambda match: (match[0], match[1].rank, match[1].display_label, match[1].weather_point_slug))
    results: list[dict] = []
    for _, row in matches:
        slug = row.weather_point_slug
        if not slug:
            continue
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

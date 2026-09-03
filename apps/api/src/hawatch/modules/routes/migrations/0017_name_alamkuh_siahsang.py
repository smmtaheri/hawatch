from __future__ import annotations

import re

from django.db import migrations


POINT_SLUG = "alamkuh_siahsang"
POINT_NAME = "قلهٔ سیاه‌سنگ علم‌کوه"
POINT_ALIASES = (
    "سیاه‌سنگ",
    "سیاه سنگ",
    "سیاه‌سنگ علم‌کوه",
    "قلهٔ سیاه‌سنگ",
    "Siah Sang",
)


def _normalize_search_text(value: str) -> str:
    text = value.strip().replace("ي", "ی").replace("ك", "ک")
    text = text.replace("\u200c", "")
    return re.sub(r"\s+", "", text).casefold()


def name_alamkuh_siahsang(apps, schema_editor):
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    RoutePoint = apps.get_model("routes", "RoutePoint")
    SearchIndexEntry = apps.get_model("catalog", "SearchIndexEntry")

    point = WeatherPoint.objects.filter(slug=POINT_SLUG).first()
    if point is None:
        return

    aliases = list(point.aliases or [])
    for alias in POINT_ALIASES:
        if alias not in aliases:
            aliases.append(alias)
    point.name = POINT_NAME
    point.aliases = aliases
    point.save(update_fields=["name", "aliases"])
    RoutePoint.objects.filter(weather_point_id=point.pk).update(name=POINT_NAME)

    existing_rows = list(
        SearchIndexEntry.objects.filter(
            kind="point",
            weather_point_slug=POINT_SLUG,
        )
    )
    if not existing_rows:
        return

    first_row = existing_rows[0]
    SearchIndexEntry.objects.filter(
        kind="point",
        weather_point_slug=POINT_SLUG,
    ).delete()

    terms = [(POINT_NAME, "name", 0), *[(alias, "alias", 1) for alias in aliases]]
    seen = set()
    search_rows = []
    for label, match_kind, rank in terms:
        normalized = _normalize_search_text(label)
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        search_rows.append(
            SearchIndexEntry(
                kind="point",
                match_kind=match_kind,
                normalized_term=normalized,
                display_label=POINT_NAME,
                display_hint=first_row.display_hint,
                destination_slug=first_row.destination_slug,
                weather_point_slug=POINT_SLUG,
                rank=rank,
                is_active=True,
            )
        )
    SearchIndexEntry.objects.bulk_create(search_rows)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_search_index"),
        ("routes", "0016_name_daryasar_spring"),
    ]

    operations = [
        migrations.RunPython(name_alamkuh_siahsang, migrations.RunPython.noop),
    ]

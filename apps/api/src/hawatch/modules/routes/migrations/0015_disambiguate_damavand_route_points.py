from __future__ import annotations

import re

from django.db import migrations


POINTS = {
    "damavand_northeast_north_join": {
        "name": "دوراهی شمالی و شمال‌شرقی دماوند",
        "aliases": (
            "محل اتصال یال شمال‌شرقی به مسیر شمالی دماوند",
            "دوراهی مسیر شمالی و شمال‌شرقی دماوند",
        ),
    },
    "damavand_sang_bozorg": {
        "name": "سنگ بزرگ دماوند",
        "aliases": (
            "سنگ بزرگ",
            "سنگ بزرگ مسیر شمالی دماوند",
        ),
    },
    "damavand_shelter_4000": {
        "name": "جان‌پناه ۴۰۰۰ دماوند",
        "aliases": (
            "جان‌پناه ۴۰۰۰",
            "پناهگاه ۴۰۰۰ دماوند",
        ),
    },
    "damavand_shelter_5000": {
        "name": "جان‌پناه ۵۰۰۰ دماوند",
        "aliases": (
            "جان‌پناه ۵۰۰۰",
            "پناهگاه ۵۰۰۰ دماوند",
        ),
    },
}


def _normalize_search_text(value: str) -> str:
    text = value.strip().replace("ي", "ی").replace("ك", "ک")
    text = text.replace("\u200c", "")
    return re.sub(r"\s+", "", text).casefold()


def _rebuild_search_rows(SearchIndexEntry, point, point_config: dict) -> None:
    existing_rows = list(
        SearchIndexEntry.objects.filter(
            kind="point",
            weather_point_slug=point.slug,
        )
    )
    if not existing_rows:
        return

    first_row = existing_rows[0]
    SearchIndexEntry.objects.filter(
        kind="point",
        weather_point_slug=point.slug,
    ).delete()

    point_name = point_config["name"]
    terms = [(point_name, "name", 0), *[(alias, "alias", 1) for alias in point.aliases]]
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
                display_label=point_name,
                display_hint=first_row.display_hint,
                destination_slug=first_row.destination_slug,
                weather_point_slug=point.slug,
                rank=rank,
                is_active=True,
            )
        )
    SearchIndexEntry.objects.bulk_create(search_rows)


def disambiguate_damavand_route_points(apps, schema_editor):
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    RoutePoint = apps.get_model("routes", "RoutePoint")
    SearchIndexEntry = apps.get_model("catalog", "SearchIndexEntry")

    for slug, point_config in POINTS.items():
        point = WeatherPoint.objects.filter(slug=slug).first()
        if point is None:
            continue

        aliases = list(point.aliases or [])
        for alias in point_config["aliases"]:
            if alias not in aliases:
                aliases.append(alias)
        point.name = point_config["name"]
        point.aliases = aliases
        point.save(update_fields=["name", "aliases"])
        RoutePoint.objects.filter(weather_point_id=point.pk).update(name=point.name)
        _rebuild_search_rows(SearchIndexEntry, point, point_config)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_search_index"),
        ("routes", "0014_name_damavand_western_parking"),
    ]

    operations = [
        migrations.RunPython(disambiguate_damavand_route_points, migrations.RunPython.noop),
    ]

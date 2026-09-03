from __future__ import annotations

import re

from django.db import migrations


POINTS = {
    "gahar_dorud_cheshmeh_khieh": {
        "name": "پارکینگ چشمه‌خیّه دورود",
        "aliases": (
            "چشمه‌خیّه · پارکینگ گهر",
            "چشمه‌خیّه دورود",
            "پارکینگ گهر",
        ),
    },
    "gahar_dorud_pambekar_pass": {
        "name": "گردنهٔ پنبه‌کار گهر",
        "aliases": (
            "گردنهٔ پنبه‌کار",
            "گردنهٔ پنبه‌کار در مسیر دورود",
        ),
    },
    "gahar_dorud_pambekar_spring": {
        "name": "چشمهٔ پنبه‌کار گهر",
        "aliases": (
            "چشمهٔ پنبه‌کار",
            "چشمهٔ پنبه‌کار در مسیر دورود",
        ),
    },
    "gahar_dorud_khodaghovat_pass": {
        "name": "گردنهٔ خداقوت گهر",
        "aliases": (
            "گردنهٔ خداقوت",
            "گردنهٔ خداقوت در مسیر دورود",
        ),
    },
    "gahar_dorud_lake_shore": {
        "name": "کرانهٔ غربی دریاچهٔ گهر",
        "aliases": ("کرانهٔ غربی گهر",),
    },
    "gahar_aligudarz_tapleh_trailhead": {
        "name": "تپهٔ تاپله الیگودرز",
        "aliases": (
            "تپهٔ تاپله · ابتدای پیاده‌روی",
            "تپهٔ تاپله",
        ),
    },
    "gahar_aligudarz_lake_view": {
        "name": "دورنمای گهر در مسیر الیگودرز",
        "aliases": (
            "اولین دورنمای دریاچهٔ گهر",
            "دورنمای دریاچهٔ گهر در مسیر الیگودرز",
        ),
    },
    "gahar_aligudarz_lake_shore": {
        "name": "کرانهٔ شرقی دریاچهٔ گهر",
        "aliases": ("کرانهٔ شرقی گهر",),
    },
    "zarrinkuh_khosravan_start": {
        "name": "روستای خسروان",
        "aliases": (
            "روستای خسروان · شروع پاکوب زرین‌کوه",
            "خسروان زرین‌کوه",
        ),
    },
    "zarrinkuh_aynehvarzan_start": {
        "name": "آیینه‌ورزان",
        "aliases": (
            "پارکینگ آینه‌ورزان · شروع مسیر زرین‌کوه",
            "آیینه ورزان",
        ),
    },
}


def _normalize_search_text(value: str) -> str:
    text = value.strip().replace("ي", "ی").replace("ك", "ک")
    text = text.replace("\u200c", "")
    return re.sub(r"\s+", "", text).casefold()


def _rebuild_search_rows(SearchIndexEntry, point) -> None:
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

    terms = [(point.name, "name", 0), *[(alias, "alias", 1) for alias in point.aliases]]
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
                display_label=point.name,
                display_hint=first_row.display_hint,
                destination_slug=first_row.destination_slug,
                weather_point_slug=point.slug,
                rank=rank,
                is_active=True,
            )
        )
    SearchIndexEntry.objects.bulk_create(search_rows)


def disambiguate_gahar_and_zarrinkuh_points(apps, schema_editor):
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
        _rebuild_search_rows(SearchIndexEntry, point)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_search_index"),
        ("routes", "0017_name_alamkuh_siahsang"),
    ]

    operations = [
        migrations.RunPython(disambiguate_gahar_and_zarrinkuh_points, migrations.RunPython.noop),
    ]

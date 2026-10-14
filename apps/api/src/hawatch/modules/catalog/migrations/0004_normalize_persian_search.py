from django.db import migrations


def rebuild_normalized_terms(apps, schema_editor):
    # These rows are derived data. Use the running search contract with
    # historical models so existing live catalogs need no re-import.
    from hawatch.modules.catalog.search_text import normalize_search_text, point_search_terms

    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    SearchIndexEntry = apps.get_model("catalog", "SearchIndexEntry")
    database = schema_editor.connection.alias
    rows = []
    for point in WeatherPoint.objects.using(database).filter(is_active=True).order_by("pk"):
        if point.slug.startswith(("dest:", "route:")):
            continue
        seen = set()
        for index, term in enumerate(point_search_terms(point)):
            normalized = normalize_search_text(term)
            if len(normalized) < 2 or normalized in seen:
                continue
            seen.add(normalized)
            rows.append(SearchIndexEntry(
                kind="point",
                match_kind="name" if index == 0 else "alias",
                normalized_term=normalized,
                display_label=point.page_name or point.name,
                display_hint="نقطهٔ شاخص" if point.importance == "primary" else "نقطهٔ مسیر",
                weather_point_slug=point.slug,
                rank=0 if point.importance == "primary" else 1,
                is_active=True,
            ))
    SearchIndexEntry.objects.using(database).all().delete()
    if rows:
        SearchIndexEntry.objects.using(database).bulk_create(rows, batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_canonical_peak_point_identities"),
        ("routes", "0026_rename_azadkouh_route_points"),
    ]

    operations = [migrations.RunPython(rebuild_normalized_terms, migrations.RunPython.noop)]

import json
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import migrations
from django.db.migrations.exceptions import IrreversibleError
from django.db.models import Q
from django.db import transaction
from django.utils import timezone


CATALOGS = (
    ("darabad_v1.json", "hawatch-darabad-catalog-v1"),
    ("dorfak_v2.json", "hawatch-dorfak-catalog-v2"),
    ("sabalan_v1.json", "hawatch-sabalan-catalog-v8"),
)

POINT_SLUG_RENAMES = {
    "darabad-chalmags-waterfall": "chal-mags-darabad",
    "darabad-haft-hoz": "haft-hoz",
    "dorfak-east-ghar-yakhi": "dorfak-ice-cave",
    "dorfak-west-shirkuh": "shirkuh-gilan",
    "dorfak-south-estakhrgah": "estakhrgah-gilan",
    "sabalan-alvares-village": "alvares-village",
    "sabalan-alvares-ski-resort": "alvares-ski-resort",
    "sabalan-gorgor-waterfall": "gorgor-waterfall",
    "sabalan-qotur-sui": "qotur-sui",
    "sabalan-moeil-village": "moeil-village",
    "sabalan-sareyn-city": "sareyn",
    "sabalan-meshgin-shahr": "meshgin-shahr",
    "sabalan-lahrud-city": "lahrud",
    "sabalan-shabil": "shabil",
    "sabalan-ne-east-hut": "sabalan-east-hut",
    "sabalan-ne-crater-lake": "sabalan-crater-lake",
}

PLACE_TYPE_CATEGORY_KEYS = {
    "summit": "mountain",
    "city": "city",
    "village": "village",
    "waterfall": "waterfall",
    "lake": "lake",
    "forest": "forest",
    "desert": "desert",
}


def forwards(apps, schema_editor):
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    Route = apps.get_model("routes", "Route")
    RoutePoint = apps.get_model("routes", "RoutePoint")
    WeekCacheInterest = apps.get_model("routes", "WeekCacheInterest")
    SearchIndexEntry = apps.get_model("catalog", "SearchIndexEntry")
    database = schema_editor.connection.alias
    reverse_renames = {new: old for old, new in POINT_SLUG_RENAMES.items()}

    for filename, old_version in CATALOGS:
        catalog_path = Path(settings.FIXTURES_DIR) / "catalog" / filename
        if not catalog_path.is_file():
            raise RuntimeError(f"Missing canonical point catalog needed for migration: {catalog_path}")
        document = json.loads(catalog_path.read_text(encoding="utf-8"))
        version = document["catalog_version"]
        primary_slug = document["point"]["slug"]

        WeatherPoint.objects.using(database).filter(
            catalog_version=old_version, fixture_managed=True
        ).update(catalog_version=version, seed_version=version)
        Route.objects.using(database).filter(
            seed_version=old_version, fixture_managed=True
        ).update(seed_version=version)
        RoutePoint.objects.using(database).filter(
            seed_version=old_version, fixture_managed=True
        ).update(seed_version=version)

        for new_slug, row in document["weather_points"].items():
            old_slug = reverse_renames.get(new_slug, new_slug)
            point = WeatherPoint.objects.using(database).filter(slug=old_slug).first()
            target = WeatherPoint.objects.using(database).filter(slug=new_slug).first()
            if old_slug != new_slug and point is not None and target is not None:
                raise RuntimeError(
                    f"Cannot rename WeatherPoint {old_slug!r}: canonical slug {new_slug!r} already exists."
                )
            if point is None and target is None:
                continue  # Fresh databases receive these rows from the catalog seed.
            if point is not None and not point.fixture_managed:
                raise RuntimeError(f"Cannot rename operator-managed WeatherPoint {old_slug!r} automatically.")
            if point is None and target is not None and not target.fixture_managed:
                raise RuntimeError(f"Cannot update operator-managed WeatherPoint {new_slug!r} automatically.")
            point = point or target

            route_points = RoutePoint.objects.using(database).filter(
                Q(weather_point_id=point.pk)
                | Q(slug=old_slug, weather_point_id__isnull=True)
            )
            for route_point in route_points:
                if RoutePoint.objects.using(database).filter(
                    route_id=route_point.route_id, slug=new_slug
                ).exclude(pk=route_point.pk).exists():
                    raise RuntimeError(
                        f"Cannot rename RoutePoint {route_point.route_id}:{old_slug} to {new_slug}: target exists."
                    )

            if old_slug != new_slug:
                old_interest = WeekCacheInterest.objects.using(database).filter(kind="point", slug=old_slug)
                if old_interest.exists() and WeekCacheInterest.objects.using(database).filter(
                    kind="point", slug=new_slug
                ).exists():
                    old_interest.delete()
                else:
                    old_interest.update(slug=new_slug)

            point.slug = new_slug
            for field in (
                "name", "page_name", "short_label", "place_type", "identity_summary",
                "importance", "name_status", "aliases", "source_urls",
            ):
                if field in row:
                    setattr(point, field, row[field])
            point.kind = row.get("kind") or "shared"
            point.seo_indexable = bool(row.get("seo_indexable", document["point"].get("seo_indexable", False)))
            seo = row.get("seo") or {}
            point.seo_title = str(seo.get("title") or "").strip()
            point.seo_description = str(seo.get("description") or "").strip()
            point.seo_content = str(seo.get("content") or "").strip()
            point.category_key = row.get("category_key") or (
                document["point"].get("category_key", "")
                if new_slug == primary_slug
                else PLACE_TYPE_CATEGORY_KEYS.get(row.get("place_type", ""), "")
            )
            point.catalog_version = version
            point.seed_version = version
            point.updated_at = timezone.now()
            point.save(using=database)

            for route_point in route_points:
                route_point.slug = new_slug
                if route_point.fixture_managed:
                    route_point.name = point.name
                route_point.save(using=database, update_fields=["slug", "name"] if route_point.fixture_managed else ["slug"])

            SearchIndexEntry.objects.using(database).filter(
                weather_point_slug__in=[old_slug, new_slug]
            ).delete()

    # Rebuild once after all point names and slugs are canonical. This keeps
    # suggestions aligned without retaining compatibility entries.
    SearchIndexEntry.objects.using(database).all().delete()
    rows = []
    for point in WeatherPoint.objects.using(database).filter(is_active=True).order_by("importance", "popular_order", "slug"):
        terms = [(point.name, "name", 0)]
        if point.page_name and point.page_name != point.name:
            terms.append((point.page_name, "alias", 1))
        terms.extend((alias, "alias", 1) for alias in point.aliases or [])
        seen = set()
        for label, match_kind, rank in terms:
            normalized = str(label or "").strip().replace("ي", "ی").replace("ك", "ک").replace("\u200c", "")
            normalized = "".join(normalized.split()).casefold()
            if len(normalized) < 2 or normalized in seen:
                continue
            seen.add(normalized)
            rows.append(SearchIndexEntry(
                kind="point",
                match_kind=match_kind,
                normalized_term=normalized,
                display_label=point.page_name or point.name,
                display_hint="نقطهٔ شاخص" if point.importance == "primary" else "نقطهٔ مسیر",
                weather_point_slug=point.slug,
                rank=max(0, rank - 1) if point.importance == "primary" else rank,
                is_active=True,
            ))
    if rows:
        SearchIndexEntry.objects.using(database).bulk_create(rows, batch_size=500)
    transaction.on_commit(lambda: cache.delete("catalog:search-index:v1"), using=database)


def backwards(apps, schema_editor):
    raise IrreversibleError(
        "Canonical point URL cleanup intentionally does not preserve old slugs or redirects."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_point_only_search"),
        ("forecasts", "0020_weather_warning_inputs"),
        ("routes", "0025_shorten_tochal_route_point_slugs"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]

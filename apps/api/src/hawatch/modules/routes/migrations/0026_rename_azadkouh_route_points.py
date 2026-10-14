import re

from django.db import migrations
from django.db.migrations.exceptions import IrreversibleError
from django.db.models import Q
from django.utils import timezone


# Existing WeatherPoint rows are renamed in place. Forecast rows and route
# endpoint foreign keys therefore keep pointing at the same physical places;
# no redirect or compatibility slug is created.
POINT_RENAMES = (
    {
        "old_slug": "azadkouh-kelakbala-start",
        "slug": "kelak-bala-baladeh",
        "name": "روستای کلاک بالا",
        "page_name": "روستای کلاک بالا بلده",
        "short_label": "کلاک بالا",
        "place_type": "village",
        "aliases": ["کلاک علیا"],
        "identity_summary": "روستای کلاک بالا در بلدهٔ نور و مبدأ مسیر رایج صعود آزادکوه",
        "importance": "primary",
        "name_status": "official",
        "kind": "primary",
        "seo_indexable": True,
        "category": "روستاهای بلده",
        "category_key": "village",
        "region": "کلاک بالا · بلده · نور · مازندران",
    },
    {
        "old_slug": "azadkouh-kelakbala-camp1",
        "slug": "kelak-camp-1",
        "name": "کمپ اول کلاک",
        "page_name": "کمپ اول کلاک",
        "short_label": "کمپ اول",
        "place_type": "camp",
        "aliases": [],
        "identity_summary": "محل کمپ اول در مسیر صعود کلاک به آزادکوه",
        "importance": "support",
        "name_status": "descriptive",
        "kind": "shared",
        "seo_indexable": False,
        "category": "",
        "category_key": "",
        "region": "",
    },
    {
        "old_slug": "azadkouh-kelakbala-camp2",
        "slug": "kelak-spring",
        "name": "چشمهٔ کلاک",
        "page_name": "چشمهٔ کلاک در مسیر آزادکوه",
        "short_label": "چشمهٔ کلاک",
        "place_type": "spring",
        "aliases": [],
        "identity_summary": "چشمهٔ فصلی مسیر کلاک، نزدیک محل کمپ دوم و پیش از گردنهٔ چورن",
        "importance": "support",
        "name_status": "descriptive",
        "kind": "shared",
        "seo_indexable": False,
        "category": "",
        "category_key": "",
        "region": "",
    },
    {
        "old_slug": "azadkouh-kelakbala-camp3",
        "slug": "kelak-camp-3",
        "name": "کمپ سوم کلاک",
        "page_name": "کمپ سوم کلاک",
        "short_label": "کمپ سوم",
        "place_type": "camp",
        "aliases": [],
        "identity_summary": "محل کمپ سوم در مسیر صعود کلاک به آزادکوه؛ در گزارش ترک دسترسی تابستانی به آب ندارد",
        "importance": "support",
        "name_status": "descriptive",
        "kind": "shared",
        "seo_indexable": False,
        "category": "",
        "category_key": "",
        "region": "",
    },
    {
        "old_slug": "azadkouh-choren-pass",
        "slug": "choren-pass",
        "name": "گردنهٔ چورن",
        "page_name": "گردنهٔ چورن آزادکوه",
        "short_label": "چورن",
        "place_type": "pass",
        "aliases": [],
        "identity_summary": "گردنهٔ چورن، گذرگاه اصلی مسیرهای کلاک، نسن و ناحیه به قلهٔ آزادکوه",
        "importance": "support",
        "name_status": "established",
        "kind": "shared",
        "seo_indexable": True,
        "category": "",
        "category_key": "",
        "region": "البرز مرکزی · آزادکوه",
    },
    {
        "old_slug": "azadkouh-nahiyeh-start",
        "slug": "nahiyeh-baladeh",
        "name": "روستای ناحیه",
        "page_name": "روستای ناحیه بلده",
        "short_label": "ناحیه",
        "place_type": "village",
        "aliases": [],
        "identity_summary": "روستای ناحیه در بلدهٔ نور و مبدأ شرقی صعود آزادکوه",
        "importance": "primary",
        "name_status": "official",
        "kind": "primary",
        "seo_indexable": True,
        "category": "روستاهای بلده",
        "category_key": "village",
        "region": "ناحیه · بلده · نور · مازندران",
    },
    {
        "old_slug": "azadkouh-nesen-start",
        "slug": "nesen",
        "name": "روستای نسن",
        "page_name": "روستای نسن",
        "short_label": "نسن",
        "place_type": "village",
        "aliases": [],
        "identity_summary": "روستای نسن در بلدهٔ نور و مبدأ مسیر شمالی صعود آزادکوه",
        "importance": "primary",
        "name_status": "official",
        "kind": "primary",
        "seo_indexable": True,
        "category": "روستاهای بلده",
        "category_key": "village",
        "region": "نسن · بلده · نور · مازندران",
    },
    {
        "old_slug": "azadkouh-varangerud-start",
        "slug": "varangeh-rud",
        "name": "روستای وارنگه‌رود",
        "page_name": "روستای وارنگه‌رود",
        "short_label": "وارنگه‌رود",
        "place_type": "village",
        "aliases": [],
        "identity_summary": "روستای وارنگه‌رود در بخش آسارا و مبدأ مسیرهای کمان‌کوه، سوتک و آزادکوه",
        "importance": "primary",
        "name_status": "official",
        "kind": "primary",
        "seo_indexable": True,
        "category": "روستاهای البرز",
        "category_key": "village",
        "region": "وارنگه‌رود · آسارا · کرج · البرز",
    },
    {
        "old_slug": "azadkouh-shirkamar-intersection",
        "slug": "sotak-pass",
        "name": "گردنهٔ سوتک",
        "page_name": "گردنهٔ سوتک",
        "short_label": "سوتک",
        "place_type": "pass",
        "aliases": [],
        "identity_summary": "گردنهٔ سوتک در بالادست درهٔ شیرکمر و نقطهٔ مشترک مسیرهای وارنگه‌رود به کمان‌کوه و آزادکوه",
        "importance": "support",
        "name_status": "established",
        "kind": "shared",
        "seo_indexable": True,
        "category": "",
        "category_key": "",
        "region": "البرز مرکزی · وارنگه‌رود",
    },
    {
        "old_slug": "azadkouh-kamankouh-lake",
        "slug": "kamankouh-lake",
        "name": "دریاچهٔ کمان‌کوه",
        "page_name": "دریاچهٔ کمان‌کوه",
        "short_label": "کمان‌کوه",
        "place_type": "lake",
        "aliases": ["برکهٔ کمان‌کوه", "برکهٔ کمانکوه"],
        "identity_summary": "دریاچهٔ فصلی مرتفع کمان‌کوه در مسیرهای کوهستانی وارنگه‌رود و آزادکوه",
        "importance": "primary",
        "name_status": "established",
        "kind": "primary",
        "seo_indexable": True,
        "category": "دریاچه‌های البرز مرکزی",
        "category_key": "lake",
        "region": "کمان‌کوه · البرز مرکزی",
    },
)

ROUTE_TEXT_UPDATES = {
    "azadkouh-kelak-bala": {
        "title": "کلاک‌بالا تا آزادکوه",
        "subtitle": "از روستای کلاک بالا و گردنهٔ چورن تا قلهٔ آزادکوه",
        "trail_label": "مسیر کلاک بالا",
        "origin": "کلاک بالا",
    },
    "azadkouh-nahiyeh": {
        "title": "ناحیهٔ بلده تا آزادکوه",
        "subtitle": "از روستای ناحیهٔ بلده و گردنهٔ چورن تا قلهٔ آزادکوه",
        "trail_label": "مسیر ناحیهٔ بلده",
        "origin": "ناحیهٔ بلده",
    },
}

POINT_METADATA_UPDATES = {
    "azadkouh": {"short_label": "آزادکوه"},
}


def _normalize_search_text(value):
    text = str(value or "").strip().replace("ي", "ی").replace("ك", "ک")
    text = text.replace("\u200c", "")
    return re.sub(r"\s+", "", text).casefold()


def _refresh_point_search_rows(SearchIndexEntry, point, database):
    SearchIndexEntry.objects.using(database).filter(weather_point_slug=point.slug).delete()
    terms = [(point.name, "name", 0)]
    if point.page_name and point.page_name != point.name:
        terms.append((point.page_name, "alias", 1))
    terms.extend((alias, "alias", 1) for alias in point.aliases or [])
    rows = []
    seen = set()
    for label, match_kind, rank in terms:
        normalized = _normalize_search_text(label)
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        rows.append(
            SearchIndexEntry(
                kind="point",
                match_kind=match_kind,
                normalized_term=normalized,
                display_label=point.page_name or point.name,
                display_hint="نقطهٔ شاخص" if point.importance == "primary" else "نقطهٔ مسیر",
                weather_point_slug=point.slug,
                rank=max(0, rank - 1) if point.importance == "primary" else rank,
                is_active=True,
            )
        )
    if rows:
        SearchIndexEntry.objects.using(database).bulk_create(rows)


def _rename_points(apps, schema_editor):
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    Route = apps.get_model("routes", "Route")
    RoutePoint = apps.get_model("routes", "RoutePoint")
    WeekCacheInterest = apps.get_model("routes", "WeekCacheInterest")
    SearchIndexEntry = apps.get_model("catalog", "SearchIndexEntry")
    database = schema_editor.connection.alias

    # Keep the catalog-version relationship graph intact when the owning
    # Azadkouh catalog advances. Access villages need this shared version to
    # link back to the mountain and to their other independent destinations.
    old_version = "hawatch-azadkouh-catalog-v7"
    new_version = "hawatch-azadkouh-catalog-v8"
    WeatherPoint.objects.using(database).filter(
        catalog_version=old_version, fixture_managed=True
    ).update(catalog_version=new_version, seed_version=new_version)
    Route.objects.using(database).filter(
        seed_version=old_version, fixture_managed=True
    ).update(seed_version=new_version)
    RoutePoint.objects.using(database).filter(
        seed_version=old_version, fixture_managed=True
    ).update(seed_version=new_version)

    for slug, values in POINT_METADATA_UPDATES.items():
        WeatherPoint.objects.using(database).filter(
            slug=slug, fixture_managed=True
        ).update(**values, updated_at=timezone.now())

    for metadata in POINT_RENAMES:
        old_slug = metadata["old_slug"]
        new_slug = metadata["slug"]
        point = WeatherPoint.objects.using(database).filter(slug=old_slug).first()
        target = WeatherPoint.objects.using(database).filter(slug=new_slug).first()
        if point is not None and target is not None:
            raise RuntimeError(
                f"Cannot rename WeatherPoint {old_slug!r}: canonical slug {new_slug!r} is already occupied."
            )
        if point is None and target is None:
            continue  # Fresh databases receive the canonical catalog at bootstrap.
        if point is not None and not point.fixture_managed:
            raise RuntimeError(f"Cannot rename operator-managed WeatherPoint {old_slug!r} automatically.")
        if point is None and target is not None and not target.fixture_managed:
            raise RuntimeError(f"Cannot update operator-managed WeatherPoint {new_slug!r} automatically.")
        point = point or target

        route_points = RoutePoint.objects.using(database).filter(
            Q(weather_point_id=point.pk) | Q(slug=old_slug, weather_point_id__isnull=True)
        )
        if route_points.exclude(weather_point_id=point.pk).exclude(weather_point_id__isnull=True).exists():
            raise RuntimeError(f"RoutePoint slug {old_slug!r} is linked to a different WeatherPoint.")
        for route_point in route_points:
            collision = RoutePoint.objects.using(database).filter(
                route_id=route_point.route_id,
                slug=new_slug,
            ).exclude(pk=route_point.pk)
            if collision.exists():
                raise RuntimeError(
                    f"Cannot rename RoutePoint {route_point.route_id}:{old_slug} to {new_slug}: target already exists."
                )

        old_interest = WeekCacheInterest.objects.using(database).filter(kind="point", slug=old_slug)
        if old_interest.exists() and WeekCacheInterest.objects.using(database).filter(
            kind="point", slug=new_slug
        ).exists():
            old_interest.delete()
        else:
            old_interest.update(slug=new_slug)

        for field, value in metadata.items():
            if field != "old_slug":
                setattr(point, field, value)
        point.is_active = True
        point.save(
            using=database,
            update_fields=[
                "slug", "name", "page_name", "short_label", "place_type", "aliases",
                "identity_summary", "importance", "name_status", "kind", "seo_indexable",
                "category", "category_key", "region", "is_active", "updated_at",
            ],
        )

        for route_point in route_points:
            route_point.slug = new_slug
            fields = ["slug"]
            if route_point.fixture_managed:
                route_point.name = point.name
                fields.append("name")
            route_point.save(using=database, update_fields=fields)

        SearchIndexEntry.objects.using(database).filter(
            weather_point_slug__in=[old_slug, new_slug]
        ).delete()
        _refresh_point_search_rows(SearchIndexEntry, point, database)

    for route_slug, values in ROUTE_TEXT_UPDATES.items():
        Route.objects.using(database).filter(slug=route_slug, fixture_managed=True).update(
            **values, updated_at=timezone.now()
        )


def forwards(apps, schema_editor):
    _rename_points(apps, schema_editor)


def backwards(apps, schema_editor):
    raise IrreversibleError(
        "Azadkouh route-point URL renames intentionally do not preserve old slugs or redirects."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0020_weather_warning_inputs"),
        ("routes", "0025_shorten_tochal_route_point_slugs"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]

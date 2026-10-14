from django.db import migrations
from django.db.migrations.exceptions import IrreversibleError
from django.db.models import Q


# Old public slug, new public slug, old name, new name, old page name,
# new page name, old short label, new short label, old indexability,
# new indexability. Coordinates, forecast rows, and point identity are kept.
POINT_RENAMES = (
    (
        "tochal-sarband-square", "sarband-tehran", "میدان سربند", "میدان سربند تهران",
        "میدان سربند، ابتدای مسیر دربند–توچال", "میدان سربند تهران", "سربند", "سربند", True, True,
    ),
    (
        "tochal-pas-ghaleh-village", "pas-ghaleh-shemiran", "روستای پس‌قلعه", "روستای پس‌قلعه شمیران",
        "روستای پس‌قلعه، ابتدای مسیر دربند–توچال", "روستای پس‌قلعه شمیران", "پس‌قلعه", "پس‌قلعه", True, True,
    ),
    (
        "tochal-shirpala-shelter", "shirpala-tochal", "پناهگاه شیرپلا", "پناهگاه شیرپلا",
        "پناهگاه شیرپلا در مسیر دربند–توچال", "پناهگاه شیرپلا توچال", "شیرپلا", "شیرپلا", True, True,
    ),
    (
        "tochal-amiri-shelter", "amiri-tochal", "جان‌پناه امیری", "جان‌پناه امیری",
        "جان‌پناه امیری در مسیر دربند–توچال", "جان‌پناه امیری توچال", "امیری", "امیری", True, True,
    ),
    (
        "tochal-goleband-ridge", "goleband-tochal", "یال گوله‌بند توچال", "یال گوله‌بند توچال",
        "یال گوله‌بند توچال", "یال گوله‌بند توچال", "یال گوله‌بند", "یال گوله‌بند", False, True,
    ),
    (
        "tochal-velenjak-parking", "velenjak-parking", "پارکینگ مجموعهٔ توچال در ولنجک", "پارکینگ توچال ولنجک",
        "پارکینگ مجموعهٔ توچال در ولنجک", "پارکینگ توچال ولنجک", "پارکینگ ولنجک", "پارکینگ ولنجک", False, False,
    ),
    (
        "tochal-telecabin-station-1", "tochal-station-1", "ایستگاه ۱ تله‌کابین توچال", "ایستگاه ۱ توچال",
        "ایستگاه ۱ تله‌کابین توچال", "ایستگاه ۱ تله‌کابین توچال", "ایستگاه ۱", "ایستگاه ۱", True, True,
    ),
    (
        "tochal-telecabin-station-2", "tochal-station-2", "ایستگاه ۲ تله‌کابین توچال", "ایستگاه ۲ توچال",
        "ایستگاه ۲ تله‌کابین توچال", "ایستگاه ۲ تله‌کابین توچال", "ایستگاه ۲", "ایستگاه ۲", True, True,
    ),
    (
        "tochal-telecabin-station-5", "tochal-station-5", "ایستگاه ۵ تله‌کابین توچال", "ایستگاه ۵ توچال",
        "ایستگاه ۵ تله‌کابین توچال", "ایستگاه ۵ تله‌کابین توچال", "ایستگاه ۵", "ایستگاه ۵", True, True,
    ),
    (
        "tochal-telecabin-station-7", "tochal-station-7", "ایستگاه ۷ تله‌کابین توچال", "ایستگاه ۷ توچال",
        "ایستگاه ۷ تله‌کابین توچال", "ایستگاه ۷ تله‌کابین توچال", "ایستگاه ۷", "ایستگاه ۷", True, True,
    ),
    (
        "tochal-kolakchal-camp", "kolakchal-camp", "پناهگاه و اردوگاه کلک‌چال", "اردوگاه کلک‌چال تهران",
        "پناهگاه و اردوگاه کلک‌چال در مسیر توچال", "اردوگاه کلک‌چال تهران", "کلک‌چال", "کلک‌چال", True, True,
    ),
    (
        "tochal-espilat-sarlo-pass", "espilat-sarlo-pass", "گردنهٔ اسپیلت–سرلو", "گردنهٔ اسپیلت–سرلو",
        "گردنهٔ اسپیلت–سرلو", "گردنهٔ اسپیلت–سرلو", "گردنهٔ اسپیلت–سرلو", "گردنهٔ اسپیلت–سرلو", False, False,
    ),
    (
        "tochal-piyazchal-pass", "piyazchal-pass", "گردنهٔ پیازچال", "گردنهٔ پیازچال",
        "گردنهٔ پیازچال", "گردنهٔ پیازچال توچال", "گردنهٔ پیازچال", "گردنهٔ پیازچال", False, True,
    ),
    (
        "tochal-lezoon-east", "lezoon-east", "قلهٔ لزون شرقی", "قلهٔ لزون شرقی",
        "قلهٔ لزون شرقی", "قلهٔ لزون شرقی توچال", "لزون شرقی", "لزون شرقی", True, True,
    ),
    (
        "tochal-lezoon-west", "lezoon-west", "قلهٔ لزون غربی", "قلهٔ لزون غربی",
        "قلهٔ لزون غربی", "قلهٔ لزون غربی توچال", "لزون غربی", "لزون غربی", True, True,
    ),
    (
        "tochal-barfchal-peak", "barfchal-tochal", "قلهٔ برف‌چال توچال", "قلهٔ برف‌چال",
        "قلهٔ برف‌چال در مسیر توچال", "قلهٔ برف‌چال توچال", "برف‌چال", "برف‌چال", True, True,
    ),
    (
        "tochal-chahar-paloon", "chahar-paloon", "قلهٔ چهارپالون", "قلهٔ چهارپالون",
        "قلهٔ چهارپالون در مسیر توچال", "قلهٔ چهارپالون توچال", "چهارپالون", "چهارپالون", True, True,
    ),
    (
        "tochal-shakarab-ahaar", "shakarab-ahar", "شکرآب آهار", "آبشار شکرآب",
        "شکرآب آهار، نقطهٔ مسیر آهار–توچال", "آبشار شکرآب آهار", "شکرآب آهار", "شکرآب", True, True,
    ),
    (
        "tochal-qezqunchal-peak", "qezqunchal-tochal", "قلهٔ قزقون‌چال", "قلهٔ قزقون‌چال",
        "قلهٔ قزقون‌چال در مسیر آهار–توچال", "قلهٔ قزقون‌چال توچال", "قزقون‌چال", "قزقون‌چال", True, True,
    ),
    (
        "tochal-homand-tochal", "homand-tochal", "قلهٔ هومند توچال", "قلهٔ هومند توچال",
        "قلهٔ هومند توچال", "قلهٔ هومند توچال", "هومند توچال", "هومند توچال", True, True,
    ),
    (
        "shahrestanak-naseri-palace", "shahrestanak-palace", "کاخ ناصری شهرستانک", "کاخ ناصری شهرستانک",
        "کاخ ناصری شهرستانک", "کاخ ناصری شهرستانک", "کاخ ناصری", "کاخ ناصری", True, True,
    ),
    (
        "tochal-shahrestanak-spring", "shahrestanak-spring", "چشمهٔ شهرستانک", "چشمهٔ شهرستانک",
        "چشمهٔ شهرستانک در مسیر توچال", "چشمهٔ شهرستانک توچال", "چشمهٔ شهرستانک", "چشمهٔ شهرستانک", False, False,
    ),
    (
        "tochal-shahrestanak-sheepfold-spring", "shahrestanak-sheepfold", "چشمه و گوسفندسرا شهرستانک", "چشمهٔ گوسفندسرا شهرستانک",
        "چشمه و گوسفندسرا شهرستانک در مسیر توچال", "چشمهٔ گوسفندسرا شهرستانک", "چشمه و گوسفندسرا", "گوسفندسرا", False, False,
    ),
    (
        "tochal-shahrestanak-pass", "shahrestanak-pass", "گردنهٔ شهرستانک", "گردنهٔ شهرستانک",
        "گردنهٔ شهرستانک در مسیر توچال", "گردنهٔ شهرستانک توچال", "گردنهٔ شهرستانک", "گردنهٔ شهرستانک", False, False,
    ),
    (
        "tochal-jamshidieh-park", "jamshidieh-park", "پارک جمشیدیه", "پارک جمشیدیه تهران",
        "پارک جمشیدیه", "پارک جمشیدیه تهران", "پارک جمشیدیه", "پارک جمشیدیه", True, True,
    ),
)

# These canonical rows already exist in the shared catalog. The Tochal
# catalog accidentally created duplicate rows for the same physical points;
# only merge these two pairs, and only after verifying identical coordinates
# and elevation. Any other occupied target slug is a hard conflict.
KNOWN_DUPLICATE_TARGETS = {
    ("tochal-shahrestanak-spring", "shahrestanak-spring"),
    ("tochal-shahrestanak-pass", "shahrestanak-pass"),
}


def _merge_forecast_dependents(apps, old_id, new_id, database):
    ForecastRecord = apps.get_model("forecasts", "ForecastRecord")
    ForecastDaily = apps.get_model("forecasts", "ForecastDaily")
    ForecastPointResolution = apps.get_model("forecasts", "ForecastPointResolution")

    for model, unique_fields in (
        (ForecastRecord, ("forecast_at", "seed_version")),
        (ForecastDaily, ("forecast_date", "seed_version")),
        (ForecastPointResolution, ("snapshot_id",)),
    ):
        rows = model.objects.using(database).filter(weather_point_id=old_id)
        for row in rows.iterator():
            identity = {field: getattr(row, field) for field in unique_fields}
            if model.objects.using(database).filter(weather_point_id=new_id, **identity).exists():
                row.delete(using=database)
            else:
                row.weather_point_id = new_id
                row.save(using=database, update_fields=["weather_point_id"])


def _same_location_and_elevation(left, right):
    return (
        left.location is not None
        and right.location is not None
        and tuple(left.location.coords) == tuple(right.location.coords)
        and left.elevation_m == right.elevation_m
    )


def _merge_duplicate_point(apps, source, target, database, *, new_name):
    RoutePoint = apps.get_model("routes", "RoutePoint")
    Route = apps.get_model("routes", "Route")
    SearchIndexEntry = apps.get_model("catalog", "SearchIndexEntry")

    route_points = RoutePoint.objects.using(database).filter(weather_point_id=source.pk)
    for route_point in route_points:
        collision = RoutePoint.objects.using(database).filter(
            route_id=route_point.route_id,
            slug=target.slug,
        ).exclude(pk=route_point.pk)
        if collision.exists():
            raise RuntimeError(
                f"Cannot merge duplicate WeatherPoint {source.slug!r}: "
                f"route {route_point.route_id} already has RoutePoint {target.slug!r}."
            )
    for route_point in route_points:
        route_point.slug = target.slug
        fields = ["slug"]
        if route_point.fixture_managed:
            route_point.name = new_name
            fields.append("name")
        route_point.save(using=database, update_fields=fields)
    RoutePoint.objects.using(database).filter(
        slug=source.slug,
        weather_point_id__isnull=True,
    ).update(slug=target.slug)

    aliases = list(target.aliases or [])
    for alias in source.aliases or []:
        if alias not in aliases:
            aliases.append(alias)
    target.aliases = aliases
    target.save(using=database, update_fields=["aliases"])

    route_points.update(weather_point_id=target.pk)
    Route.objects.using(database).filter(origin_weather_point_id=source.pk).update(
        origin_weather_point_id=target.pk
    )
    Route.objects.using(database).filter(target_weather_point_id=source.pk).update(
        target_weather_point_id=target.pk
    )
    _merge_forecast_dependents(apps, source.pk, target.pk, database)

    # Search rows for the duplicate are superseded by the canonical target's
    # entries; do not keep duplicate/stale names as a hidden URL fallback.
    SearchIndexEntry.objects.using(database).filter(weather_point_slug=source.slug).delete()
    source.delete(using=database)


def _rename_tochal_points(apps, schema_editor):
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    RoutePoint = apps.get_model("routes", "RoutePoint")
    WeekCacheInterest = apps.get_model("routes", "WeekCacheInterest")
    SearchIndexEntry = apps.get_model("catalog", "SearchIndexEntry")
    database = schema_editor.connection.alias

    for values in POINT_RENAMES:
        (
            old_slug, new_slug, old_name, new_name, old_page_name, new_page_name,
            old_short_label, new_short_label, old_indexable, new_indexable,
        ) = values
        source_slug, target_slug = old_slug, new_slug
        point_name, page_name, short_label, indexable = new_name, new_page_name, new_short_label, new_indexable

        point = WeatherPoint.objects.using(database).filter(slug=source_slug).first()
        target = WeatherPoint.objects.using(database).filter(slug=target_slug).first()
        if point is None:
            if target is not None:
                continue  # Already renamed by an operator before this migration.
            continue  # Fresh databases receive the canonical catalog after migrate.
        if not point.fixture_managed:
            raise RuntimeError(f"Cannot rename operator-managed WeatherPoint {source_slug!r} automatically.")
        if target is not None:
            if (
                (source_slug, target_slug) not in KNOWN_DUPLICATE_TARGETS
                or not target.fixture_managed
                or not _same_location_and_elevation(point, target)
            ):
                raise RuntimeError(
                    f"Cannot rename WeatherPoint {source_slug!r}: target {target_slug!r} already exists "
                    "and is not a verified catalog duplicate."
                )
            _merge_duplicate_point(apps, point, target, database, new_name=point_name)
            point = target

        if target is None:
            related_route_points = RoutePoint.objects.using(database).filter(
                Q(weather_point_id=point.pk) | Q(slug=source_slug, weather_point_id__isnull=True)
            )
            if related_route_points.exclude(weather_point_id=point.pk).exclude(weather_point_id__isnull=True).exists():
                raise RuntimeError(f"RoutePoint slug {source_slug!r} is linked to a different WeatherPoint.")
            for route_point in related_route_points:
                collision = RoutePoint.objects.using(database).filter(
                    route_id=route_point.route_id,
                    slug=target_slug,
                ).exclude(pk=route_point.pk).exists()
                if collision:
                    raise RuntimeError(
                        f"Cannot rename RoutePoint {route_point.route_id}:{source_slug} to {target_slug}: target already exists."
                    )

        # For verified duplicates, source has been merged and deleted; for a
        # regular rename this updates the existing canonical row in place.
        point.slug = target_slug
        point.name = point_name
        point.page_name = page_name
        point.short_label = short_label
        point.seo_indexable = indexable
        point.is_active = True
        point.save(
            using=database,
            update_fields=["slug", "name", "page_name", "short_label", "seo_indexable", "is_active", "updated_at"],
        )
        if target is None:
            for route_point in related_route_points:
                # Slug is the canonical link key. Preserve operator-managed route
                # labels, while aligning fixture-owned labels with the new point name.
                route_point.slug = target_slug
                fields = ["slug"]
                if route_point.fixture_managed:
                    route_point.name = point_name
                    fields.append("name")
                route_point.save(using=database, update_fields=fields)
            SearchIndexEntry.objects.using(database).filter(
                weather_point_slug=source_slug
            ).update(weather_point_slug=target_slug, display_label=page_name)

        old_interest = WeekCacheInterest.objects.using(database).filter(kind="point", slug=source_slug)
        if old_interest.exists():
            if WeekCacheInterest.objects.using(database).filter(kind="point", slug=target_slug).exists():
                old_interest.delete()
            else:
                old_interest.update(slug=target_slug)


def forwards(apps, schema_editor):
    _rename_tochal_points(apps, schema_editor)


def backwards(apps, schema_editor):
    raise IrreversibleError(
        "This migration removes duplicate WeatherPoint rows and cannot restore deleted IDs or URLs."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0020_weather_warning_inputs"),
        ("routes", "0024_weekcacheinterest"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]

# Additive Destination ↔ WeatherPoint profile link with safe forecast merge.

from django.db import migrations, models
import django.db.models.deletion

# Explicit Destination.slug → WeatherPoint.slug mappings that are known-safe.
KNOWN_DESTINATION_WEATHER_POINT_SLUGS = {
    "touchal": "tochal_summit",
}


def _merge_forecast_records(ForecastRecord, synthetic_id, canonical_id):
    for record in ForecastRecord.objects.filter(weather_point_id=synthetic_id).iterator():
        conflict = ForecastRecord.objects.filter(
            weather_point_id=canonical_id,
            # ``forecast_at`` can differ by sub-second precision between two
            # legacy ingest rows.  ``hour_bucket`` is the stable logical slot
            # used by the forecast pipeline, so use it to avoid duplicating the
            # same hourly reading while moving synthetic destination data.
            hour_bucket=record.hour_bucket,
            seed_version=record.seed_version,
        ).exists()
        if conflict:
            continue
        record.weather_point_id = canonical_id
        record.save(update_fields=["weather_point_id"])


def _merge_forecast_daily(ForecastDaily, synthetic_id, canonical_id):
    for row in ForecastDaily.objects.filter(weather_point_id=synthetic_id).iterator():
        conflict = ForecastDaily.objects.filter(
            weather_point_id=canonical_id,
            forecast_date=row.forecast_date,
            seed_version=row.seed_version,
        ).exists()
        if conflict:
            continue
        row.weather_point_id = canonical_id
        row.save(update_fields=["weather_point_id"])


def _merge_forecast_resolutions(ForecastPointResolution, synthetic_id, canonical_id):
    for row in ForecastPointResolution.objects.filter(weather_point_id=synthetic_id).iterator():
        conflict = ForecastPointResolution.objects.filter(
            weather_point_id=canonical_id,
            snapshot_id=row.snapshot_id,
        ).exists()
        if conflict:
            continue
        row.weather_point_id = canonical_id
        row.save(update_fields=["weather_point_id"])


def _merge_synthetic_into_canonical(apps, synthetic, canonical):
    """Move non-conflicting dependent rows; never delete the synthetic WeatherPoint."""
    if synthetic is None or canonical is None or synthetic.id == canonical.id:
        return
    ForecastRecord = apps.get_model("forecasts", "ForecastRecord")
    ForecastDaily = apps.get_model("forecasts", "ForecastDaily")
    ForecastPointResolution = apps.get_model("forecasts", "ForecastPointResolution")
    _merge_forecast_records(ForecastRecord, synthetic.id, canonical.id)
    _merge_forecast_daily(ForecastDaily, synthetic.id, canonical.id)
    _merge_forecast_resolutions(ForecastPointResolution, synthetic.id, canonical.id)


def _is_proven_destination_canonical(point, destination) -> bool:
    """True only when ownership/type prove the point is this destination's canonical place."""
    if point is None or destination is None:
        return False
    if str(getattr(point, "slug", "")).startswith("dest:"):
        return False
    return (
        point.destination_id == destination.id
        and point.kind == "destination"
    )


def backfill_destination_weather_points(apps, schema_editor):
    Destination = apps.get_model("destinations", "Destination")
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")

    for destination in Destination.objects.all():
        synthetic = WeatherPoint.objects.filter(slug=f"dest:{destination.slug}").first()

        canonical = None
        if destination.weather_point_id:
            canonical = WeatherPoint.objects.filter(pk=destination.weather_point_id).first()

        if canonical is None:
            proven = (
                WeatherPoint.objects.filter(destination_id=destination.id, kind="destination")
                .exclude(slug__startswith="dest:")
                .order_by("id")
            )
            canonical = proven.first()

        if canonical is None:
            mapped_slug = KNOWN_DESTINATION_WEATHER_POINT_SLUGS.get(destination.slug)
            if mapped_slug:
                canonical = WeatherPoint.objects.filter(slug=mapped_slug).first()

        if canonical is None:
            desired_slug = destination.slug
            existing = WeatherPoint.objects.filter(slug=desired_slug).first()
            if existing is not None:
                if _is_proven_destination_canonical(existing, destination):
                    canonical = existing
                else:
                    # Ambiguous slug collision with an unrelated catalog/route point.
                    # Do not link or merge; leave destination.weather_point unresolved.
                    continue
            elif synthetic is not None:
                # Create a stable canonical copy; leave synthetic dest:{slug} intact.
                canonical = WeatherPoint.objects.create(
                    slug=desired_slug,
                    name=synthetic.name,
                    aliases=list(getattr(synthetic, "aliases", None) or []),
                    kind="destination",
                    location=synthetic.location,
                    elevation_m=synthetic.elevation_m,
                    elevation_source=getattr(synthetic, "elevation_source", "") or "",
                    destination_id=destination.id,
                    climate=synthetic.climate,
                    status=getattr(synthetic, "status", "approved") or "approved",
                    provenance=getattr(synthetic, "provenance", "demo_fixture") or "demo_fixture",
                    catalog_version=getattr(synthetic, "catalog_version", "") or "",
                    data_mode=synthetic.data_mode,
                    seed_version=synthetic.seed_version,
                )

        if canonical is None:
            continue

        _merge_synthetic_into_canonical(apps, synthetic, canonical)

        if destination.weather_point_id != canonical.id:
            destination.weather_point_id = canonical.id
            destination.save(update_fields=["weather_point_id"])


class Migration(migrations.Migration):
    """
    Additive + reversible strategy:
    - Forward: add O2O, backfill Destination.weather_point, merge non-conflicting
      forecast dependents from dest:{slug} into the canonical WeatherPoint.
    - Never adopt a WeatherPoint solely because slug == Destination.slug; ownership
      (destination FK + kind=destination) or an explicit known mapping is required.
    - Ambiguous slug collisions leave Destination.weather_point null and do not merge.
    - Reverse: migrations.RunPython.noop so reverse does not wipe associations before
      the field drop; migrated forecast ownership stays on the canonical point.
      Synthetic dest:* rows are never deleted.
    """

    dependencies = [
        ("destinations", "0003_destination_aliases"),
        ("forecasts", "0011_search_aliases"),
    ]

    operations = [
        migrations.AddField(
            model_name="destination",
            name="weather_point",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="destination_profile",
                to="forecasts.weatherpoint",
            ),
        ),
        migrations.RunPython(backfill_destination_weather_points, migrations.RunPython.noop),
    ]

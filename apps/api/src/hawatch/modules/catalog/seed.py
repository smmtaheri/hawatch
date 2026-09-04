from __future__ import annotations

import glob
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone as dj_timezone

from hawatch.common.time import ALL_HOURS, day_window, hour_bucket, localize_dt, now_tehran
from hawatch.integrations.weather.demo import generate_reading, supported_climate_keys
from hawatch.modules.catalog.catalog import load_catalog_file, seed_catalog
from hawatch.modules.catalog.search import rebuild_search_index
from hawatch.modules.forecasts.models import DemoSeedState, ForecastRecord, WeatherPoint

DATA_MODE = "demo"


def ensure_catalog(seed_version: str) -> dict[str, WeatherPoint]:
    """Import packaged catalogs after the owners of their shared points.

    Filename order is not a catalog dependency contract: a newly added catalog
    can reference a shared Point in any existing catalog.  Resolve those
    dependencies from the versioned documents before the first bootstrap so a
    fresh database is reproducible and does not depend on stale test data.
    """

    documents = {
        Path(path).relative_to(settings.FIXTURES_DIR).as_posix(): load_catalog_file(
            Path(path).relative_to(settings.FIXTURES_DIR).as_posix()
        )
        for path in sorted(glob.glob(str(Path(settings.FIXTURES_DIR) / "catalog/*_v*.json")))
    }
    owners: dict[str, str] = {}
    for relative, document in documents.items():
        for slug in document["weather_points"]:
            existing_owner = owners.setdefault(slug, relative)
            if existing_owner != relative:
                raise ValueError(f"WeatherPoint {slug} has multiple catalog owners: {existing_owner}, {relative}")

    dependencies = {
        relative: {
            owners[slug]
            for slug in document.get("shared_weather_points") or []
            if slug in owners and owners[slug] != relative
        }
        for relative, document in documents.items()
    }
    ordered_catalogs: list[str] = []
    remaining = set(documents)
    while remaining:
        ready = sorted(relative for relative in remaining if dependencies[relative] <= set(ordered_catalogs))
        if not ready:
            blocked = "; ".join(
                f"{relative} -> {', '.join(sorted(dependencies[relative] & remaining))}"
                for relative in sorted(remaining)
            )
            raise ValueError(f"Catalog shared-point dependency cycle: {blocked}")
        ordered_catalogs.extend(ready)
        remaining.difference_update(ready)

    result: dict[str, WeatherPoint] = {}
    for relative in ordered_catalogs:
        seed_catalog(catalog_file=relative, prune=False, force_adopt=False, rebuild_search=False)
    result.update({point.slug: point for point in WeatherPoint.objects.filter(data_mode="live")})
    rebuild_search_index()
    return result


def ensure_forecasts(seed_version: str, *, force: bool = False) -> DemoSeedState:
    local = now_tehran()
    bucket = hour_bucket(local)
    state, created = DemoSeedState.objects.get_or_create(key="demo", defaults={"seed_version": seed_version, "last_hour_bucket": "", "generated_at": dj_timezone.now(), "local_date": local.date(), "local_hour": local.hour})
    if not force and not created and state.last_hour_bucket == bucket and state.seed_version == seed_version:
        return state
    generated_at = dj_timezone.now()
    points = list(
        WeatherPoint.objects.filter(is_active=True)
        .exclude(slug__startswith="dest:")
        .exclude(slug__startswith="route:")
    )
    supported_climates = supported_climate_keys()
    invalid_points = [point for point in points if point.climate not in supported_climates]
    if invalid_points:
        details = ", ".join(f"{point.slug}={point.climate!r}" for point in invalid_points)
        allowed = ", ".join(sorted(supported_climates))
        raise ValueError(
            "Cannot generate demo forecasts; unsupported climate profile(s): "
            f"{details}. Allowed values: {allowed}"
        )

    records = []
    for point in points:
        elevation = point.elevation_m or 2000
        for day in day_window(local.date()):
            for hour in ALL_HOURS:
                reading = generate_reading(point_slug=point.slug, climate_key=point.climate, elevation_m=elevation, local_date=day, hour=hour)
                forecast_at = localize_dt(day, hour)
                records.append(ForecastRecord(weather_point=point, snapshot=None, forecast_at=forecast_at, valid_from=forecast_at, valid_to=forecast_at + timedelta(hours=2), generated_at=generated_at, hour_bucket=bucket, **{key: reading[key] for key in ("temperature_c", "apparent_temperature_c", "weather_code", "condition_label", "icon", "wind_speed_kmh", "wind_gust_kmh", "wind_direction_deg", "precipitation_probability", "precipitation_mm", "rain_mm", "snowfall_cm", "visibility_km", "cloud_cover_pct", "uv_index", "freezing_level_m", "cloud_base_m", "severity")}, freshness=ForecastRecord.Freshness.READY, data_mode=DATA_MODE, source="hawatch-demo", seed_version=seed_version, provider="demo"))
    with transaction.atomic():
        ForecastRecord.objects.filter(seed_version=seed_version, data_mode=DATA_MODE).delete()
        ForecastRecord.objects.bulk_create(records, batch_size=500)
        state.seed_version, state.last_hour_bucket, state.generated_at, state.local_date, state.local_hour = seed_version, bucket, generated_at, local.date(), local.hour
        state.save()
    return state


def seed_demo_data(*, force: bool = False) -> DemoSeedState | None:
    if not settings.DEMO_DATA_ENABLED:
        return DemoSeedState.objects.filter(key="demo").first()
    seed_version = settings.DEMO_SEED_VERSION
    # Catalog import is bootstrap-only. Once live points exist, generating or
    # refreshing demo forecasts must not overwrite operator-managed edits made
    # through Admin or an explicit catalog import.
    if not WeatherPoint.objects.filter(is_active=True, data_mode="live").exists():
        ensure_catalog(seed_version)
    return ensure_forecasts(seed_version, force=force)


def refresh_if_bucket_changed() -> DemoSeedState | None:
    if not settings.DEMO_DATA_ENABLED:
        return None

    # API reads must not re-import the JSON catalog on every request. Apart
    # from unnecessary work, that would overwrite operator edits (for example
    # a deliberately pending RoutePoint) before the serializer can observe
    # them. Re-seed only when the demo clock bucket or seed version changed;
    # callers that explicitly need a catalog refresh use force=True.
    local = now_tehran()
    bucket = hour_bucket(local)
    state = DemoSeedState.objects.filter(key="demo").first()
    if state and state.seed_version == settings.DEMO_SEED_VERSION and state.last_hour_bucket == bucket:
        return state
    return seed_demo_data(force=False)

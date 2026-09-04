from __future__ import annotations

import glob
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone as dj_timezone

from hawatch.common.time import ALL_HOURS, day_window, hour_bucket, localize_dt, now_tehran
from hawatch.integrations.weather.demo import generate_reading
from hawatch.modules.catalog.catalog import seed_catalog
from hawatch.modules.catalog.search import rebuild_search_index
from hawatch.modules.forecasts.models import DemoSeedState, ForecastRecord, WeatherPoint

DATA_MODE = "demo"


def ensure_catalog(seed_version: str) -> dict[str, WeatherPoint]:
    result: dict[str, WeatherPoint] = {}
    for path in sorted(glob.glob(str(Path(settings.FIXTURES_DIR) / "catalog/*_v*.json"))):
        relative = Path(path).relative_to(settings.FIXTURES_DIR).as_posix()
        seed_catalog(catalog_file=relative, prune=False, force_adopt=False)
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
    records = []
    for point in WeatherPoint.objects.filter(is_active=True).exclude(slug__startswith="dest:").exclude(slug__startswith="route:"):
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
    ensure_catalog(seed_version)
    return ensure_forecasts(seed_version, force=force)


def refresh_if_bucket_changed() -> DemoSeedState | None:
    return seed_demo_data(force=False) if settings.DEMO_DATA_ENABLED else None

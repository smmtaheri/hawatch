from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from hawatch.modules.forecasts.models import (
    DemoSeedState,
    ForecastPointResolution,
    ForecastRecord,
    ForecastSnapshot,
    WeatherPoint,
)


@admin.register(WeatherPoint)
class WeatherPointAdmin(GISModelAdmin):
    list_display = ("slug", "kind", "name", "elevation_m", "status", "catalog_version")
    list_filter = ("kind", "status", "provenance", "data_mode")


@admin.register(ForecastSnapshot)
class ForecastSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "status", "freshness", "point_count", "generated_at", "checksum")
    list_filter = ("provider", "status", "freshness")


@admin.register(ForecastPointResolution)
class ForecastPointResolutionAdmin(admin.ModelAdmin):
    list_display = (
        "weather_point",
        "snapshot",
        "requested_elevation_m",
        "resolved_elevation_m",
        "elevation_requested",
    )


@admin.register(ForecastRecord)
class ForecastRecordAdmin(admin.ModelAdmin):
    list_display = ("weather_point", "forecast_at", "temperature_c", "severity", "freshness", "provider")
    list_filter = ("severity", "freshness", "data_mode", "provider")


@admin.register(DemoSeedState)
class DemoSeedStateAdmin(admin.ModelAdmin):
    list_display = ("key", "seed_version", "last_hour_bucket", "generated_at")

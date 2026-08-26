from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from hawatch.modules.forecasts.models import DemoSeedState, ForecastRecord, WeatherPoint


@admin.register(WeatherPoint)
class WeatherPointAdmin(GISModelAdmin):
    list_display = ("slug", "kind", "name", "elevation_m")


@admin.register(ForecastRecord)
class ForecastRecordAdmin(admin.ModelAdmin):
    list_display = ("weather_point", "forecast_at", "temperature_c", "severity", "freshness")
    list_filter = ("severity", "freshness", "data_mode")


@admin.register(DemoSeedState)
class DemoSeedStateAdmin(admin.ModelAdmin):
    list_display = ("key", "seed_version", "last_hour_bucket", "generated_at")

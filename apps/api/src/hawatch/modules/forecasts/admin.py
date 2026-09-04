from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.db import transaction

from hawatch.modules.catalog.search import rebuild_search_index
from hawatch.modules.forecasts.models import (
    DemoSeedState,
    ForecastPointResolution,
    ForecastRecord,
    ForecastSnapshot,
    WeatherPoint,
)


def _rebuild_search_after_commit() -> None:
    transaction.on_commit(rebuild_search_index)


@admin.register(WeatherPoint)
class WeatherPointAdmin(GISModelAdmin):
    list_display = (
        "slug",
        "kind",
        "name",
        "elevation_m",
        "status",
        "is_active",
        "ingest_enabled",
        "fixture_managed",
        "catalog_version",
        "updated_at",
    )
    list_filter = (
        "kind",
        "status",
        "provenance",
        "data_mode",
        "is_active",
        "ingest_enabled",
        "fixture_managed",
    )
    search_fields = ("slug", "name")
    readonly_fields = ("updated_at", "fixture_managed")
    fieldsets = (
        (None, {"fields": ("slug", "name", "page_name", "short_label", "aliases", "kind", "importance", "seo_indexable")}),
        ("Profile", {"fields": ("tile_name", "short_category", "category", "category_key", "region", "image", "image_alt", "is_popular", "popular_order")}),
        ("Location", {"fields": ("location", "elevation_m", "elevation_source", "status")}),
        (
            "Runtime",
            {
                "fields": (
                    "is_active",
                    "ingest_enabled",
                    "climate",
                    "provenance",
                    "catalog_version",
                    "data_mode",
                    "seed_version",
                    "fixture_managed",
                    "updated_at",
                )
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _rebuild_search_after_commit()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        _rebuild_search_after_commit()

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        _rebuild_search_after_commit()


@admin.register(ForecastSnapshot)
class ForecastSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "provider",
        "status",
        "freshness",
        "point_count",
        "catalog_version",
        "generated_at",
        "checksum",
    )
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

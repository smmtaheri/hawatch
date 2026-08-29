from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.db import transaction

from hawatch.modules.catalog.search import rebuild_search_index
from hawatch.modules.destinations.models import Destination


def _rebuild_search_after_commit() -> None:
    transaction.on_commit(rebuild_search_index)


@admin.register(Destination)
class DestinationAdmin(GISModelAdmin):
    list_display = ("slug", "name", "region", "is_popular", "is_active", "weather_point")
    list_filter = ("is_popular", "is_active", "data_mode")
    search_fields = ("slug", "name", "tile_name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("weather_point",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "slug",
                    "tile_name",
                    "name",
                    "short_category",
                    "category",
                    "category_key",
                    "region",
                    "aliases",
                )
            },
        ),
        ("Location", {"fields": ("location", "elevation_m", "image", "image_alt")}),
        (
            "Profile / runtime",
            {
                "fields": (
                    "weather_point",
                    "climate",
                    "is_popular",
                    "popular_order",
                    "is_active",
                    "data_mode",
                    "seed_version",
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

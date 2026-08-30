from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from hawatch.modules.routes.models import Route, RoutePoint
from hawatch.modules.routes.publish import normalize_and_publish_route, schedule_search_index_rebuild


class RoutePointInline(admin.TabularInline):
    model = RoutePoint
    extra = 0
    autocomplete_fields = ("weather_point", "destination")
    fields = (
        "sort_order",
        "slug",
        "weather_point",
        "name",
        "cumulative_minutes",
        "segment_minutes",
        "timing_status",
        "elevation_m",
        "public_note",
        "internal_note",
        "fixture_managed",
    )
    readonly_fields = ("fixture_managed", "internal_note")
    ordering = ("sort_order",)


@admin.register(Route)
class RouteAdmin(GISModelAdmin):
    list_display = (
        "slug",
        "title",
        "destination",
        "timing_status",
        "one_way_minutes",
        "is_active",
        "featured",
        "fixture_managed",
        "updated_at",
    )
    list_filter = ("timing_status", "is_active", "featured", "fixture_managed", "data_mode")
    search_fields = ("slug", "title", "origin")
    readonly_fields = ("updated_at", "fixture_managed")
    inlines = [RoutePointInline]
    autocomplete_fields = ("destination", "origin_weather_point", "target_weather_point")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "slug",
                    "destination",
                    "title",
                    "subtitle",
                    "trail_label",
                    "origin",
                    "destination_label",
                    "region",
                    "featured",
                    "sort_order",
                    "is_active",
                )
            },
        ),
        (
            "Geometry / distance",
            {
                "fields": (
                    "distance_km",
                    "ascent_m",
                    "origin_location",
                    "origin_weather_point",
                    "target_weather_point",
                )
            },
        ),
        (
            "Timing / provenance",
            {
                "fields": (
                    "timing_status",
                    "one_way_minutes",
                    "default_start_minutes",
                    "timing_method",
                    "timing_version",
                    "timing_confidence",
                    "timing_uncertainty_minutes",
                    "timing_source_urls",
                    "round_trip_minutes",
                )
            },
        ),
        (
            "Catalog",
            {
                "fields": (
                    "catalog_key",
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

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        normalize_and_publish_route(form.instance, rebuild_search=True)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        schedule_search_index_rebuild()

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        schedule_search_index_rebuild()


@admin.register(RoutePoint)
class RoutePointAdmin(GISModelAdmin):
    list_display = (
        "slug",
        "name",
        "route",
        "sort_order",
        "cumulative_minutes",
        "timing_status",
        "fixture_managed",
    )
    list_filter = ("timing_status", "data_mode", "fixture_managed")
    search_fields = ("slug", "name", "route__slug")
    autocomplete_fields = ("route", "weather_point", "destination")
    # Research/provenance may be inspected here but must not be edited as UI copy.
    readonly_fields = ("fixture_managed", "internal_note")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.route_id:
            normalize_and_publish_route(obj.route, rebuild_search=True)

    def delete_model(self, request, obj):
        route = obj.route
        super().delete_model(request, obj)
        if route is not None:
            normalize_and_publish_route(route, rebuild_search=True)

    def delete_queryset(self, request, queryset):
        routes = {item.route_id: item.route for item in queryset.select_related("route")}
        super().delete_queryset(request, queryset)
        for route in routes.values():
            if route is not None:
                normalize_and_publish_route(route, rebuild_search=False)
        schedule_search_index_rebuild()

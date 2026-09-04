from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django import forms
from django.db import transaction

from hawatch.modules.catalog.search import rebuild_search_index
from hawatch.modules.forecasts.models import (
    DemoSeedState,
    ForecastPointResolution,
    ForecastRecord,
    ForecastSnapshot,
    WeatherPoint,
    WeatherProxy,
)
from hawatch.common.proxy import masked_proxy_uri, validate_proxy_uri


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


class WeatherProxyAdminForm(forms.ModelForm):
    proxy_url = forms.CharField(
        label="آدرس پروکسی",
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text="socks5:// یا socks5h://؛ مقدار قبلی را برای حفظ آن خالی بگذارید.",
    )

    class Meta:
        model = WeatherProxy
        fields = "__all__"

    def clean_proxy_url(self):
        value = self.cleaned_data.get("proxy_url", "").strip()
        if not value and self.instance.pk:
            return self.instance.proxy_url
        if not value:
            raise forms.ValidationError("آدرس پروکسی الزامی است.")
        try:
            return validate_proxy_uri(value)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc


@admin.register(WeatherProxy)
class WeatherProxyAdmin(admin.ModelAdmin):
    form = WeatherProxyAdminForm
    list_display = (
        "name",
        "country_code",
        "masked_uri",
        "sort_order",
        "is_active",
        "failure_count",
        "last_used_at",
        "last_success_at",
        "last_failure_at",
    )
    list_filter = ("country_code", "is_active")
    ordering = ("sort_order", "pk")
    readonly_fields = ("masked_uri", "last_used_at", "last_success_at", "last_failure_at", "failure_count", "last_error", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "country_code", "proxy_url", "sort_order", "is_active")}),
        ("وضعیت اتصال", {"fields": ("masked_uri", "failure_count", "last_error", "last_used_at", "last_success_at", "last_failure_at")}),
        ("سیستم", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="نشانی mask‌شده")
    def masked_uri(self, obj):
        return masked_proxy_uri(obj.proxy_url)

    def has_module_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_add_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)


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

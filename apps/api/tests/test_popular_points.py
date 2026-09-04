"""Regression tests for ordered popular points on the home endpoint."""

import pytest
from django.contrib.gis.geos import Point
from django.core.management import call_command
from rest_framework.test import APIClient

from hawatch.api.v1.serializers import list_points
from hawatch.modules.catalog.runtime import publicly_visible_weather_points
from hawatch.modules.catalog.seed import seed_demo_data
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_home_point_list_contains_only_ordered_popular_four():
    seed_demo_data(force=True)
    call_command("set_popular_points", "--slugs", "gahar,tochal,azadkouh,sabalan")

    assert [item.slug for item in list_points()] == ["gahar", "tochal", "azadkouh", "sabalan"]
    assert WeatherPoint.objects.filter(is_popular=True).count() == 4
    assert WeatherPoint.objects.get(slug="darabad").is_popular is False


@pytest.mark.django_db
def test_packaged_home_defaults_and_catalog_sync_keep_popular_selection():
    seed_demo_data(force=True)
    assert [item.slug for item in list_points()] == ["tochal", "damavand", "alamkuh", "tar-lake"]

    call_command("set_popular_points", "--slugs", "tochal,damavand,alamkuh,tar-lake")
    call_command("sync_catalog", "--apply")

    assert [item.slug for item in list_points()] == ["tochal", "damavand", "alamkuh", "tar-lake"]


@pytest.mark.django_db
def test_new_point_is_not_popular_by_default():
    point = WeatherPoint.objects.create(
        slug="new-point",
        name="نقطهٔ جدید",
        page_name="نقطهٔ جدید",
        short_label="نقطهٔ جدید",
        place_type="landmark",
        identity_summary="نقطهٔ جدید برای تست",
        importance="support",
        name_status="descriptive",
        source_urls=["https://example.test/new-point"],
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.4, 35.8, srid=4326),
        elevation_m=1000,
        data_mode="live",
    )

    assert point.is_popular is False


@pytest.mark.django_db
def test_home_api_exposes_active_catalog_counts_not_popular_tile_count(api_client):
    seed_demo_data(force=True)
    WeatherPoint.objects.filter(slug="darabad").update(is_active=False)
    route = Route.objects.filter(target_weather_point__slug="tochal").first()
    assert route is not None
    route.is_active = False
    route.save(update_fields=["is_active"])

    response = api_client.get("/api/v1/points/")

    assert response.status_code == 200
    assert response.json()["meta"]["catalog_counts"] == {
        "points": WeatherPoint.objects.filter(is_active=True).count(),
        "routes": Route.objects.filter(is_active=True).count(),
    }
    assert publicly_visible_weather_points().count() >= 1

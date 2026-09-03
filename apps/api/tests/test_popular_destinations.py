import pytest
from django.contrib.gis.geos import Point
from django.core.management import call_command
from rest_framework.test import APIClient

from hawatch.api.v1.serializers import list_destinations
from hawatch.modules.catalog.seed import seed_demo_data
from hawatch.modules.catalog.runtime import publicly_visible_weather_points
from hawatch.modules.destinations.models import Destination
from hawatch.modules.routes.models import Route


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_home_destination_list_contains_only_ordered_popular_four():
    seed_demo_data(force=True)
    call_command(
        "set_popular_destinations",
        "--slugs",
        "gahar,tochal,damavand,daryasar",
    )

    assert [item.slug for item in list_destinations()] == ["gahar", "tochal", "damavand", "daryasar"]
    assert Destination.objects.filter(is_popular=True).count() == 4
    assert Destination.objects.get(slug="maranjab").is_popular is False


@pytest.mark.django_db
def test_new_destination_is_not_popular_by_default():
    destination = Destination.objects.create(
        slug="new-destination",
        tile_name="مقصد جدید",
        name="مقصد جدید",
        short_category="کوه",
        category="کوه",
        category_key="mountain",
        region="ایران",
        elevation_m=1000,
        location=Point(51.4, 35.8, srid=4326),
        image="/images/fallback.png",
        image_alt="مقصد جدید",
        climate="alpine",
    )

    assert destination.is_popular is False


@pytest.mark.django_db
def test_home_api_exposes_active_catalog_counts_not_popular_tile_count(api_client):
    seed_demo_data(force=True)
    Destination.objects.filter(slug="maranjab").update(is_active=False)
    route = Route.objects.filter(destination__slug="tochal").first()
    assert route is not None
    route.is_active = False
    route.save(update_fields=["is_active"])

    response = api_client.get("/api/v1/destinations/")

    assert response.status_code == 200
    assert response.json()["meta"]["catalog_counts"] == {
        "destinations": Destination.objects.filter(is_active=True).count(),
        "routes": Route.objects.filter(is_active=True, destination__is_active=True).count(),
        "points": publicly_visible_weather_points().count(),
    }

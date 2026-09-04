"""Regression: active/inactive point, route, search, and ingest visibility."""

from __future__ import annotations

from django.contrib.gis.geos import Point
from rest_framework.test import APIClient

import pytest

from hawatch.modules.catalog.runtime import ingestible_weather_points
from hawatch.modules.catalog.search import rebuild_search_index, search_suggestions
from hawatch.modules.catalog.tochal import seed_tochal_catalog
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tochal(db):
    return seed_tochal_catalog()


@pytest.mark.django_db
def test_inactive_route_hidden_from_point_routes_siblings_and_endpoint(api_client, tochal):
    Route.objects.filter(slug="tochal-kolakchal").update(is_active=False)

    point = api_client.get("/api/v1/points/tochal/").json()["point"]
    assert "tochal-kolakchal" not in {item["slug"] for item in point["routes"]}

    siblings = api_client.get("/api/v1/routes/tochal-darband/").json()["route"]["siblings"]
    assert "tochal-kolakchal" not in {item["slug"] for item in siblings}
    assert api_client.get("/api/v1/routes/tochal-kolakchal/forecast/").status_code == 404


@pytest.mark.django_db
def test_inactive_point_returns_404(api_client, tochal):
    WeatherPoint.objects.filter(slug="tochal-sarband-square").update(is_active=False)

    assert api_client.get("/api/v1/points/tochal-sarband-square/").status_code == 404
    assert api_client.get("/api/v1/points/tochal-sarband-square/forecast/").status_code == 404


@pytest.mark.django_db
def test_related_routes_require_active_route(api_client, tochal):
    Route.objects.filter(slug="tochal-darband").update(is_active=False)
    body = api_client.get("/api/v1/points/tochal-goleband-ridge/forecast/").json()

    assert "tochal-darband" not in {item["slug"] for item in body["related_routes"]}
    assert "tochal-kolakchal" in {item["slug"] for item in body["related_routes"]}


@pytest.mark.django_db
def test_ingest_ignores_unlinked_non_indexable_point(tochal):
    orphan = WeatherPoint.objects.create(
        slug="orphan-point",
        name="نقطهٔ یتیم",
        page_name="نقطهٔ یتیم",
        short_label="نقطهٔ یتیم",
        place_type="landmark",
        identity_summary="نقطهٔ یتیم برای تست",
        importance="support",
        name_status="descriptive",
        source_urls=["https://example.test/orphan"],
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.41, 35.87, srid=4326),
        elevation_m=3000,
        data_mode="live",
        is_active=True,
        ingest_enabled=True,
        fixture_managed=False,
        seo_indexable=False,
    )
    assert orphan.slug not in list(ingestible_weather_points().values_list("slug", flat=True))


@pytest.mark.django_db
def test_ingest_keeps_active_indexable_point_when_its_routes_are_inactive(tochal):
    point = WeatherPoint.objects.get(slug="tochal-sarband-square")
    Route.objects.filter(points__weather_point=point).update(is_active=False)
    # All public Points are now indexable by policy, so ingest does not depend
    # on at least one active Route for this point.
    assert point.slug in list(ingestible_weather_points().values_list("slug", flat=True))

    Route.objects.filter(points__weather_point=point).update(is_active=True)
    point.is_active = False
    point.save(update_fields=["is_active"])
    assert point.slug not in list(ingestible_weather_points().values_list("slug", flat=True))


@pytest.mark.django_db
def test_search_hides_inactive_point_but_keeps_primary_point(tochal):
    rebuild_search_index()
    assert any(item["slug"] == "tochal-sarband-square" for item in search_suggestions(query="سربند"))

    WeatherPoint.objects.filter(slug="tochal-sarband-square").update(is_active=False)
    rebuild_search_index()
    assert search_suggestions(query="سربند") == []
    assert any(item["slug"] == "tochal" for item in search_suggestions(query="توچال"))

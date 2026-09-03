"""Regression: active/inactive public visibility, search, and ingest eligibility."""

from __future__ import annotations

from django.contrib.gis.geos import Point
from rest_framework.test import APIClient

import pytest

from hawatch.modules.catalog.runtime import ingestible_weather_points
from hawatch.modules.catalog.search import rebuild_search_index, search_suggestions
from hawatch.modules.catalog.tochal import seed_tochal_catalog
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tochal(db):
    return seed_tochal_catalog()


@pytest.mark.django_db
def test_inactive_route_hidden_from_lists_siblings_and_direct_endpoint(api_client, tochal):
    route = Route.objects.get(slug="tochal-kolakchal")
    route.is_active = False
    route.save(update_fields=["is_active"])

    dest = api_client.get("/api/v1/destinations/tochal/forecast/").json()
    assert "tochal-kolakchal" not in {item["slug"] for item in dest["related_routes"]}
    assert "tochal-kolakchal" not in {item["slug"] for item in dest["destination"]["routes"]}

    siblings = api_client.get("/api/v1/routes/tochal-darband/forecast/").json()["route"]["siblings"]
    assert "tochal-kolakchal" not in {item["slug"] for item in siblings}

    assert api_client.get("/api/v1/routes/tochal-kolakchal/forecast/").status_code == 404


@pytest.mark.django_db
def test_inactive_destination_hides_routes_and_returns_404(api_client, tochal):
    destination = Destination.objects.get(slug="tochal")
    destination.is_active = False
    destination.save(update_fields=["is_active"])

    assert api_client.get("/api/v1/destinations/tochal/forecast/").status_code == 404
    assert api_client.get("/api/v1/routes/tochal-darband/forecast/").status_code == 404
    assert api_client.get("/api/v1/points/tochal-sarband-square/forecast/").status_code == 404


@pytest.mark.django_db
def test_inactive_weather_point_returns_404(api_client, tochal):
    point = WeatherPoint.objects.get(slug="tochal-sarband-square")
    point.is_active = False
    point.save(update_fields=["is_active"])
    assert api_client.get("/api/v1/points/tochal-sarband-square/forecast/").status_code == 404


@pytest.mark.django_db
def test_related_routes_require_active_route_and_destination(api_client, tochal):
    # goleband is on both darband and kalkchal; deactivating only darband must hide it.
    Route.objects.filter(slug="tochal-darband").update(is_active=False)
    body = api_client.get("/api/v1/points/tochal-goleband-ridge/forecast/").json()
    assert body["related_routes"]
    assert "tochal-darband" not in {item["slug"] for item in body["related_routes"]}
    assert "tochal-kolakchal" in {item["slug"] for item in body["related_routes"]}


@pytest.mark.django_db
def test_ingest_ignores_legacy_destination_fk_alone(tochal):
    destination = Destination.objects.get(slug="tochal")
    orphan = WeatherPoint.objects.create(
        slug="org_only_point",
        name="فقط سازمانی",
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.41, 35.87, srid=4326),
        elevation_m=3000,
        destination=destination,
        data_mode="live",
        is_active=True,
        ingest_enabled=True,
        fixture_managed=False,
    )
    assert orphan.slug not in list(ingestible_weather_points().values_list("slug", flat=True))


@pytest.mark.django_db
def test_ingest_excludes_inactive_route_and_destination(tochal):
    point = WeatherPoint.objects.get(slug="tochal-sarband-square")
    Route.objects.filter(points__weather_point=point).update(is_active=False)
    # Still on inactive routes only → not ingestible unless profile.
    assert "tochal-sarband-square" not in list(ingestible_weather_points().values_list("slug", flat=True))

    Route.objects.filter(points__weather_point=point).update(is_active=True)
    Destination.objects.filter(slug="tochal").update(is_active=False)
    assert "tochal-sarband-square" not in list(ingestible_weather_points().values_list("slug", flat=True))
    assert "tochal_summit" not in list(ingestible_weather_points().values_list("slug", flat=True))


@pytest.mark.django_db
def test_search_hides_inactive_route_destination_and_point(tochal):
    rebuild_search_index()
    assert any(item["slug"] == "tochal-sarband-square" for item in search_suggestions(query="سربند"))

    Route.objects.filter(slug="tochal-darband").update(is_active=False)
    rebuild_search_index()
    # sarband only on darband among routes that include it as origin — if only inactive, drop.
    # Keep a control: summit still on other active routes.
    assert any(item["slug"] == "tochal_summit" or item["type"] == "destination" for item in search_suggestions(query="توچال"))

    Destination.objects.filter(slug="tochal").update(is_active=False)
    rebuild_search_index()
    assert search_suggestions(query="توچال") == []
    assert search_suggestions(query="سربند") == []

    Destination.objects.filter(slug="tochal").update(is_active=True)
    Route.objects.filter(slug="tochal-darband").update(is_active=True)
    WeatherPoint.objects.filter(slug="tochal-sarband-square").update(is_active=False)
    rebuild_search_index()
    assert not any(item["slug"] == "tochal-sarband-square" for item in search_suggestions(query="سربند"))

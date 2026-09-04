"""Regression tests for the point-only catalog identity migration."""

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from hawatch.modules.catalog.catalog import seed_catalog
from hawatch.modules.catalog.seed import seed_demo_data
from hawatch.modules.catalog.tochal import seed_tochal_catalog
from hawatch.modules.forecasts.models import WeatherPoint


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seeded(db):
    return seed_demo_data(force=True)


@pytest.mark.django_db
def test_primary_point_is_the_only_canonical_profile():
    seed_demo_data(force=True)
    point = WeatherPoint.objects.get(slug="tochal")

    assert point.kind == WeatherPoint.Kind.PRIMARY
    assert point.seo_indexable is True
    assert point.elevation_m == 3955
    assert not WeatherPoint.objects.filter(slug__startswith="dest:").exists()
    assert not WeatherPoint.objects.filter(slug__startswith="route:").exists()


@pytest.mark.django_db
def test_seed_idempotent_never_creates_synthetic_points():
    seed_demo_data(force=True)
    seed_catalog()
    seed_catalog()

    assert WeatherPoint.objects.filter(slug="tochal").count() == 1
    assert not WeatherPoint.objects.filter(slug__startswith="dest:").exists()
    assert not WeatherPoint.objects.filter(slug__startswith="route:").exists()


@pytest.mark.django_db
def test_operator_managed_point_is_not_overwritten_by_catalog_import():
    seed_tochal_catalog()
    point = WeatherPoint.objects.get(slug="tochal")
    point.name = "قلهٔ دستی"
    point.fixture_managed = False
    point.save(update_fields=["name", "fixture_managed"])

    result = seed_tochal_catalog()

    assert any("tochal" in item for item in result["conflicts"])
    assert WeatherPoint.objects.get(slug="tochal").name == "قلهٔ دستی"


@pytest.mark.django_db
def test_active_route_point_uses_its_own_canonical_href(api_client):
    seed_demo_data(force=True)
    response = api_client.get(
        "/api/v1/points/tochal-sarband-square/forecast/",
        {"date": "2026-08-28", "period": "morning"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["subject"]["slug"] == "tochal-sarband-square"
    assert body["subject"]["canonical_href"] == "/points/tochal-sarband-square"
    assert body["point"]["href"] == "/points/tochal-sarband-square"
    assert body["forecast"]["meta"]["selected_period"] == "morning"


@pytest.mark.django_db
def test_search_has_one_result_for_primary_point(api_client, seeded):
    results = api_client.get("/api/v1/search/suggestions/", {"q": "توچال"}).json()["results"]
    matches = [item for item in results if item["slug"] == "tochal"]

    assert len(matches) == 1
    assert matches[0]["type"] == "point"
    assert matches[0]["href"] == "/points/tochal"


@pytest.mark.django_db
def test_route_planner_period_exposes_step_and_hourly_slots(api_client, seeded):
    body = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "06:00"},
    ).json()
    period = body["period"]

    assert period["planner_step_minutes"] == 60
    assert period["planner_start_minutes"] == 360
    assert period["planner_last_start_minutes"] == 660
    assert period["planner_slots"] == [360, 420, 480, 540, 600, 660]
    assert len(period["planner_ticks"]) == 6

    night = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "night", "start_time": "20:00"},
    ).json()["period"]
    assert night["planner_end_minutes"] == 1440
    assert night["planner_last_start_minutes"] == 1380
    assert night["planner_slots"] == [1080, 1140, 1200, 1260, 1320, 1380]
    assert len(night["planner_ticks"]) == 6

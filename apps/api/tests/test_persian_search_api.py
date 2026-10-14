from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.db import connection

from hawatch.modules.catalog.models import SearchIndexEntry
from hawatch.modules.forecasts.models import WeatherPoint


@pytest.mark.django_db
def test_public_search_surfaces_match_persian_spelling_variants(api_client, seeded):
    cases = {
        "damavand": ["قله دماوند", "قله ی دماوند", "قله‌ی دماوند", "قلۀ دماوند", "قلهٔ دماوند"],
        "alamkuh": ["علمکوه", "علم کوه", "علم‌کوه", "قله ي علمكوه"],
        "tar-lake": ["دریاچه تار", "دریاچه ی تار", "دریاچه‌ی تار"],
        "azadkouh": ["آزادکوه", "ازادکوه", "آزاد کوه"],
    }
    for slug, queries in cases.items():
        for query in queries:
            for path, parameter, field in [
                ("search/suggestions/", "q", "results"),
                ("destinations/", "query", "destinations"),
                ("points/", "query", "results"),
            ]:
                response = api_client.get(f"/api/v1/{path}", {parameter: query})
                assert response.status_code == 200, (path, query)
                matches = [item["slug"] for item in response.json()[field]]
                assert matches.count(slug) == 1, (path, query, matches)

    for query in ["توچال دربند", "دربند توچال", "قله ی توچال دربند"]:
        routes = api_client.get("/api/v1/routes/", {"query": query}).json()["routes"]
        suggestions = api_client.get("/api/v1/search/suggestions/", {"q": query, "include_routes": "1"}).json()["results"]
        assert "tochal-darband" in [item["slug"] for item in routes], query
        assert "tochal-darband" in [item["slug"] for item in suggestions], query

    for query in ["جان پناه 4000", "جان‌پناه ۴۰۰۰", "جان پناه ٤٠٠٠"]:
        matches = api_client.get("/api/v1/search/suggestions/", {"q": query}).json()["results"]
        assert "damavand-shelter-4000" in [item["slug"] for item in matches], query

    assert WeatherPoint.objects.get(slug="damavand").name == "قلهٔ دماوند"


@pytest.mark.django_db
def test_search_upgrade_rebuilds_existing_index_without_changing_points(api_client, seeded):
    SearchIndexEntry.objects.filter(weather_point_slug="damavand").update(normalized_term="قلهٔدماوند")
    before = list(WeatherPoint.objects.order_by("pk").values("pk", "slug", "name", "page_name", "seo_indexable"))
    migration = import_module("hawatch.modules.catalog.migrations.0004_normalize_persian_search")
    migration.rebuild_normalized_terms(apps, SimpleNamespace(connection=connection))

    assert list(WeatherPoint.objects.order_by("pk").values("pk", "slug", "name", "page_name", "seo_indexable")) == before
    results = api_client.get("/api/v1/search/suggestions/", {"q": "قله ی دماوند"}).json()["results"]
    assert results[0]["slug"] == "damavand"
    assert sum(item["slug"] == "damavand" for item in results) == 1

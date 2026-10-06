import json
from pathlib import Path

import pytest

from hawatch.api.v1.serializers import related_routes_for_weather_point
from hawatch.modules.catalog.catalog import seed_catalog
from hawatch.modules.catalog.validation import validate_catalog_document
from hawatch.modules.forecasts.models import WeatherPoint


CATALOG = "catalog/katale-khor_v1.json"
SLUG = "katale-khor"
NAME = "غار کتله‌خور"


def test_katale_khor_is_one_documented_cave_entrance_without_a_hiking_route():
    catalog = json.loads((Path(__file__).parents[1] / "fixtures" / CATALOG).read_text())
    assert not validate_catalog_document(catalog)
    assert catalog["primary_point"] == SLUG
    assert catalog["routes"] == {}
    assert list(catalog["weather_points"]) == [SLUG]
    point = catalog["weather_points"][SLUG]
    assert point["name"] == point["page_name"] == catalog["point"]["name"] == NAME
    assert point["category_key"] == catalog["point"]["category_key"] == "cave"
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (
        35.8360367, 48.1621486, 1729
    )
    assert "غار کتله خور" in point["aliases"]
    assert "نه هوای داخل غار" in point["identity_summary"]
    assert "https://www.openstreetmap.org/node/3096058666" in point["source_urls"]
    assert not catalog["point"]["is_popular"]


@pytest.mark.django_db
def test_katale_khor_has_an_indexable_canonical_page_and_sitemap_entry(api_client):
    seed_catalog(catalog_file=CATALOG, raise_on_conflict=True)
    point = WeatherPoint.objects.get(slug=SLUG)
    assert point.is_active and point.seo_indexable and point.ingest_enabled
    assert point.kind == WeatherPoint.Kind.PRIMARY and point.importance == "primary"
    assert point.category_key == "cave"
    assert point.name == point.page_name == NAME
    assert not related_routes_for_weather_point(point)
    response = api_client.get(f"/points/{SLUG}")
    assert response.status_code == 200
    assert response["X-Robots-Tag"] == "index,follow"
    assert NAME in response.content.decode()
    assert f"https://hawatch.ir/points/{SLUG}" in response.content.decode()
    sitemap = api_client.get("/api/v1/seo/sitemap.xml")
    assert sitemap.status_code == 200
    assert f"https://hawatch.ir/points/{SLUG}</loc>" in sitemap.content.decode()

import json
from pathlib import Path

import pytest

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOG = "catalog/shah_dezh_alborz_v1.json"
SLUG = "shah-dezh-alborz"
NAME = "قلهٔ شاه‌دژ البرز"


def test_shah_dezh_is_documented_without_publishing_a_technical_hiking_route():
    catalog = json.loads((Path(__file__).parents[1] / "fixtures" / CATALOG).read_text())
    assert not validate_catalog_document(catalog)
    assert len(catalog["catalog_version"]) <= 32
    assert catalog["primary_point"] == SLUG
    assert list(catalog["weather_points"]) == [SLUG]
    point = catalog["weather_points"][SLUG]
    assert catalog["routes"] == point["routes"] == {}
    assert point["name"] == point["page_name"] == catalog["point"]["name"] == NAME
    assert point["place_type"] == "summit"
    assert point["category_key"] == catalog["point"]["category_key"] == "mountain"
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (35.944998, 51.134172, 2798)
    assert point["status"] == "provisional"
    assert "DEM" in point["elevation_source"]
    assert "نسام دار" in point["aliases"]
    assert "نسام در" in point["aliases"]
    assert "بالاده" in point["identity_summary"]
    assert "برای پیاده‌روی عمومی مناسب نیست" in point["seo"]["description"]
    assert point["aliases"] == catalog["point"]["aliases"]
    assert not catalog["point"]["is_popular"]


@pytest.mark.django_db
def test_shah_dezh_has_an_indexable_canonical_page_and_sitemap_entry(api_client):
    from hawatch.api.v1.serializers import related_routes_for_weather_point
    from hawatch.modules.catalog.catalog import seed_catalog
    from hawatch.modules.forecasts.models import WeatherPoint

    seed_catalog(catalog_file=CATALOG, raise_on_conflict=True)
    point = WeatherPoint.objects.get(slug=SLUG)
    assert point.is_active and point.seo_indexable and point.ingest_enabled
    assert point.kind == WeatherPoint.Kind.PRIMARY and point.importance == "primary"
    assert point.name == point.page_name == NAME
    assert not related_routes_for_weather_point(point)
    response = api_client.get(f"/points/{SLUG}")
    assert response.status_code == 200
    assert response["X-Robots-Tag"] == "index,follow"
    html = response.content.decode()
    assert NAME in html
    assert f"https://hawatch.ir/points/{SLUG}" in html
    sitemap = api_client.get("/api/v1/seo/sitemap.xml")
    assert sitemap.status_code == 200
    assert f"https://hawatch.ir/points/{SLUG}</loc>" in sitemap.content.decode()

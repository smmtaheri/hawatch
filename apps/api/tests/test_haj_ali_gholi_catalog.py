import json
from pathlib import Path

import pytest

from hawatch.api.v1.serializers import related_routes_for_weather_point
from hawatch.modules.catalog.catalog import seed_catalog
from hawatch.modules.catalog.validation import validate_catalog_document
from hawatch.modules.forecasts.models import WeatherPoint


CATALOG = "catalog/haj_ali_gholi_v1.json"
SLUG = "haj-ali-gholi"
NAME = "کویر حاج‌علی‌قلی دامغان"


def test_haj_ali_gholi_is_one_documented_desert_without_a_fabricated_route():
    catalog = json.loads((Path(__file__).parents[1] / "fixtures" / CATALOG).read_text())
    assert not validate_catalog_document(catalog)
    assert catalog["routes"] == {}
    assert list(catalog["weather_points"]) == [SLUG]
    point = catalog["weather_points"][SLUG]
    assert point["name"] == point["page_name"] == catalog["point"]["name"] == NAME
    assert point["place_type"] == catalog["point"]["category_key"] == "desert"
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (
        35.915194, 54.740583, 1053
    )
    assert "دریاچه نمک حاج علی قلی" in point["aliases"]
    assert point["source_urls"]


@pytest.mark.django_db
def test_haj_ali_gholi_has_an_indexable_canonical_page_and_sitemap_entry(api_client):
    seed_catalog(catalog_file=CATALOG, raise_on_conflict=True)
    point = WeatherPoint.objects.get(slug=SLUG)
    assert point.is_active and point.seo_indexable and point.ingest_enabled
    assert point.kind == WeatherPoint.Kind.PRIMARY and point.importance == "primary"
    assert point.climate == "desert" and point.category_key == "desert"
    assert point.name == point.page_name == NAME
    assert not related_routes_for_weather_point(point)

    response = api_client.get(f"/points/{SLUG}")
    assert response.status_code == 200
    assert response["X-Robots-Tag"] == "index,follow"
    html = response.content.decode()
    assert NAME in html
    assert f'https://hawatch.ir/points/{SLUG}' in html
    sitemap = api_client.get("/api/v1/seo/sitemap.xml")
    assert sitemap.status_code == 200
    assert f"https://hawatch.ir/points/{SLUG}</loc>" in sitemap.content.decode()

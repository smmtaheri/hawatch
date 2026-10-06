import json
from pathlib import Path

import pytest

from hawatch.api.v1.serializers import related_routes_for_weather_point
from hawatch.modules.catalog.catalog import seed_catalog
from hawatch.modules.catalog.validation import validate_catalog_document
from hawatch.modules.forecasts.models import WeatherPoint


VILLAGES = [
    ("catalog/sheet_tarom_v1.json", "sheet-tarom", "روستای شیت طارم", 36.9780234, 48.6996499, 907),
    ("catalog/validar_v1.json", "validar", "روستای ولیدر", 36.96972, 48.63139, 1567),
]


@pytest.mark.parametrize("filename,slug,name,latitude,longitude,elevation", VILLAGES)
def test_tarom_village_is_documented_and_point_only(filename, slug, name, latitude, longitude, elevation):
    catalog = json.loads((Path(__file__).parents[1] / "fixtures" / filename).read_text())
    assert not validate_catalog_document(catalog)
    assert catalog["primary_point"] == slug
    assert catalog["routes"] == {}
    assert list(catalog["weather_points"]) == [slug]
    point = catalog["weather_points"][slug]
    assert point["routes"] == {}
    assert point["name"] == point["page_name"] == catalog["point"]["name"] == name
    assert point["place_type"] == point["category_key"] == catalog["point"]["category_key"] == "village"
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (latitude, longitude, elevation)
    assert point["source_urls"]
    assert point["seo_indexable"] and catalog["point"]["seo_indexable"]
    assert point["aliases"] == catalog["point"]["aliases"]


@pytest.mark.django_db
@pytest.mark.parametrize("filename,slug,name,latitude,longitude,elevation", VILLAGES)
def test_tarom_village_has_an_indexable_page_and_sitemap_entry(
    api_client, filename, slug, name, latitude, longitude, elevation
):
    seed_catalog(catalog_file=filename, raise_on_conflict=True)
    point = WeatherPoint.objects.get(slug=slug)
    assert point.is_active and point.seo_indexable and point.ingest_enabled
    assert point.kind == WeatherPoint.Kind.PRIMARY and point.importance == "primary"
    assert point.place_type == point.category_key == "village"
    assert point.name == point.page_name == name
    assert not related_routes_for_weather_point(point)
    response = api_client.get(f"/points/{slug}")
    assert response.status_code == 200
    assert response["X-Robots-Tag"] == "index,follow"
    html = response.content.decode()
    assert name in html
    assert f"https://hawatch.ir/points/{slug}" in html
    sitemap = api_client.get("/api/v1/seo/sitemap.xml")
    assert sitemap.status_code == 200
    assert f"https://hawatch.ir/points/{slug}</loc>" in sitemap.content.decode()

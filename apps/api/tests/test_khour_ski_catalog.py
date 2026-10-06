import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOG_DIR = Path(__file__).parents[1] / "fixtures/catalog"


def test_khour_ski_is_an_independent_indexable_point_with_ski_icon():
    catalog = json.loads((CATALOG_DIR / "khour_ski_v1.json").read_text())
    assert not validate_catalog_document(catalog)
    assert catalog["primary_point"] == catalog["point"]["slug"] == "khour-ski"
    assert set(catalog["weather_points"]) == {"khour-ski"}
    assert catalog["routes"] == {}  # road access / ski slopes are not hiking routes
    profile = catalog["point"]
    point = catalog["weather_points"]["khour-ski"]
    assert point["name"] == point["page_name"] == point["short_label"] == profile["name"] == "پیست اسکی خور"
    assert point["category_key"] == profile["category_key"] == "ski"
    assert point["place_type"] == "landmark"  # specific category takes precedence
    assert point["kind"] == point["importance"] == "primary"
    assert point["seo_indexable"] is profile["seo_indexable"] is True
    assert profile["is_active"] is True
    assert profile["is_popular"] is False
    for field in ("latitude", "longitude", "elevation_m", "climate"):
        assert point[field] == profile[field]
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (35.91135, 51.1698, 2632)
    assert point["source_urls"] and point["elevation_source"]
    assert "Khur Ski Resort" in point["aliases"]
    existing = json.loads((CATALOG_DIR / "pahneh_hesar_v1.json").read_text())["weather_points"]
    for slug in ("khour-village", "khour-waterfall"):
        assert slug != catalog["primary_point"]
        assert (existing[slug]["latitude"], existing[slug]["longitude"]) != (point["latitude"], point["longitude"])

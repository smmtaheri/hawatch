import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOG = Path(__file__).parents[1] / "fixtures/catalog/taleghan_dam_v1.json"


def test_taleghan_dam_and_reservoir_share_one_indexable_destination():
    catalog = json.loads(CATALOG.read_text())
    assert not validate_catalog_document(catalog)
    assert catalog["primary_point"] == catalog["point"]["slug"] == "taleghan-dam"
    assert list(catalog["weather_points"]) == ["taleghan-dam"]
    point = catalog["weather_points"]["taleghan-dam"]
    assert point["name"] == point["page_name"] == point["short_label"] == catalog["point"]["name"] == "سد طالقان"
    assert point["seo_indexable"] and point["kind"] == point["importance"] == "primary"
    assert point["category_key"] == catalog["point"]["category_key"] == "dam"
    assert point["place_type"] == "lake" and point["climate"] == "lake_valley"
    assert "دریاچه سد طالقان" in point["aliases"]
    assert "دریاچه طالقان" in point["aliases"]
    assert "طالقان" not in point["aliases"]  # city is a distinct future destination
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (36.175556, 50.673333, 1764)
    assert point["source_urls"] and point["elevation_source"]


def test_reservoir_access_is_not_invented_as_a_hiking_route():
    catalog = json.loads(CATALOG.read_text())
    assert catalog["routes"] == {}
    assert not catalog["point"]["is_popular"]

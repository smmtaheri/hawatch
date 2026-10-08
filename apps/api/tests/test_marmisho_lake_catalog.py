import json
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "fixtures/catalog/marmisho_lake_v1.json"


def test_marmisho_lake_is_an_indexable_point_only_destination():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    point = catalog["weather_points"]["marmisho-lake"]

    assert catalog["primary_point"] == catalog["point"]["slug"] == "marmisho-lake"
    assert point["name"] == point["page_name"] == point["short_label"] == "دریاچهٔ مارمیشو"
    assert point["kind"] == point["importance"] == "primary"
    assert point["seo_indexable"] is True
    assert point["place_type"] == point["category_key"] == "lake"
    assert catalog["routes"] == {}
    assert point["source_urls"]
    assert point["elevation_source"]

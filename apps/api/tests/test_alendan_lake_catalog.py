import json
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "fixtures" / "catalog" / "alendan_lake_v1.json"


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def test_alendan_lake_is_an_indexable_point_only_destination():
    catalog = load_catalog()
    point = catalog["weather_points"]["alendan-lake"]

    assert catalog["primary_point"] == "alendan-lake"
    assert catalog["routes"] == {}
    assert point["place_type"] == "lake"
    assert point["category_key"] == "lake"
    assert point["kind"] == "primary"
    assert point["importance"] == "primary"
    assert point["seo_indexable"] is True
    assert "آب‌بندان پله ازنی" in point["aliases"]

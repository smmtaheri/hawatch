import json
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "fixtures" / "catalog" / "kandolus_village_v1.json"


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def test_kandolus_is_an_indexable_point_only_village_destination():
    catalog = load_catalog()
    point = catalog["weather_points"]["kandolus-village"]
    forest = catalog["weather_points"]["kojur-forest"]

    assert catalog["catalog_version"] == "hawatch-kandolus-v2"
    assert catalog["primary_point"] == "kandolus-village"
    assert catalog["routes"] == {}
    assert point["place_type"] == "village"
    assert point["category_key"] == "village"
    assert point["kind"] == "primary"
    assert point["importance"] == "primary"
    assert point["seo_indexable"] is True
    assert "کندلوس نوشهر" in point["aliases"]
    assert forest["name"] == "جنگل کجور"
    assert forest["place_type"] == "forest"
    assert forest["category_key"] == "forest"
    assert forest["kind"] == "primary"
    assert forest["importance"] == "primary"
    assert forest["seo_indexable"] is True

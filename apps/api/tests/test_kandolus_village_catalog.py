import json
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "fixtures" / "catalog" / "kandolus_village_v1.json"


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def test_kandolus_catalog_keeps_village_and_adds_sisangan_route_cluster():
    catalog = load_catalog()
    point = catalog["weather_points"]["kandolus-village"]
    forest = catalog["weather_points"]["kojur-forest"]
    mine = catalog["weather_points"]["kojur-coal-mine"]
    moss_waterfall = catalog["weather_points"]["kojur-moss-waterfall"]
    waterfall = catalog["weather_points"]["sisangan-waterfall"]
    sisangan = catalog["weather_points"]["sisangan-forest-park"]
    route = catalog["routes"]["kojur-to-sisangan-waterfall"]

    assert catalog["catalog_version"] == "hawatch-kandolus-v3"
    assert catalog["primary_point"] == "kandolus-village"
    assert "kojur-to-sisangan-waterfall" in catalog["routes"]
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
    assert mine["place_type"] == "landmark"
    assert mine["seo_indexable"] is False
    assert moss_waterfall["place_type"] == "waterfall"
    assert waterfall["name"] == "آبشار سیسنگان"
    assert waterfall["seo_indexable"] is False
    assert sisangan["name"] == "پارک جنگلی سیسنگان"
    assert sisangan["seo_indexable"] is True
    assert sisangan["place_type"] == "forest"
    assert route["points"] == [
        "kojur-coal-mine",
        "kojur-moss-waterfall",
        "sisangan-waterfall",
    ]
    assert route["distance_km"] == 14.48
    assert route["timing"]["cumulative_minutes"]["sisangan-waterfall"] == 480

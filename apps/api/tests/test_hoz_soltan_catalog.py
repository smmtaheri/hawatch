import json
from pathlib import Path


def test_hoz_soltan_is_an_indexable_point_only_lake_destination():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/hoz_soltan_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))
    point = catalog["weather_points"]["hoz-soltan"]

    assert catalog["primary_point"] == "hoz-soltan"
    assert catalog["routes"] == {}
    assert point["name"] == "دریاچهٔ حوض سلطان"
    assert point["place_type"] == "lake"
    assert point["category_key"] == "lake"
    assert point["seo_indexable"] is True
    assert point["latitude"] == 35.00328
    assert point["longitude"] == 50.93649
    assert catalog["point"]["slug"] == "hoz-soltan"

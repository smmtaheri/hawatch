import json
from pathlib import Path


def test_barfkhaneh_is_an_indexable_point_only_summit():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/barfkhaneh_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))
    point = catalog["weather_points"]["barfkhaneh"]

    assert catalog["primary_point"] == "barfkhaneh"
    assert catalog["routes"] == {}
    assert point["name"] == "قلهٔ برفخانهٔ طزرجان"
    assert point["place_type"] == "summit"
    assert point["category_key"] == "mountain"
    assert point["seo_indexable"] is True
    assert (point["latitude"], point["longitude"]) == (31.5485, 54.1474)
    assert catalog["point"]["slug"] == "barfkhaneh"

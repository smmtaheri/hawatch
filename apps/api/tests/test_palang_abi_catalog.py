import json
from pathlib import Path


def test_palang_abi_is_an_indexable_point_only_summit():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/palang_abi_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))
    point = catalog["weather_points"]["palang-abi"]

    assert catalog["primary_point"] == "palang-abi"
    assert catalog["routes"] == {}
    assert point["name"] == "قلهٔ پلنگ‌آبی"
    assert point["place_type"] == "summit"
    assert point["category_key"] == "ridge"
    assert point["seo_indexable"] is True
    assert point["latitude"] == 34.219255
    assert point["longitude"] == 50.810666
    assert catalog["point"]["slug"] == "palang-abi"

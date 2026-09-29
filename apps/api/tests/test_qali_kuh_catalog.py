import json
from pathlib import Path


def test_qali_kuh_is_an_indexable_point_only_peak():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/qali_kuh_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "qali-kuh"
    assert catalog["routes"] == {}
    point = catalog["weather_points"]["qali-kuh"]
    assert point["seo_indexable"] is True
    assert point["place_type"] == "summit"
    assert point["latitude"] == 33.0586142
    assert point["longitude"] == 49.48661

import json
from pathlib import Path


def test_qali_kuh_has_an_indexable_peak_and_validated_hiking_route():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/qali_kuh_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "qali-kuh"
    point = catalog["weather_points"]["qali-kuh"]
    assert point["seo_indexable"] is True
    assert point["place_type"] == "summit"
    assert point["latitude"] == 33.0586142
    assert point["longitude"] == 49.48661
    route = catalog["routes"]["qali_kuh_pamzareh"]
    assert route["slug"] == "qali-kuh-pamzareh-summit"
    assert route["points"] == [
        "qali-kuh-pamzareh-trailhead",
        "qali-kuh-sar-juibar",
        "qali-kuh",
    ]
    assert route["timing_status"] == "estimated"

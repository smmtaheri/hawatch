import json
from pathlib import Path


def test_bisotun_has_an_indexable_peak_and_hiking_route():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/bisotun_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "bisotun"
    point = catalog["weather_points"]["bisotun"]
    assert point["seo_indexable"] is True
    assert point["place_type"] == "summit"
    assert point["latitude"] == 34.3888819
    route = catalog["routes"]["bisotun_police_road"]
    assert route["slug"] == "bisotun-police-road-summit"
    assert route["points"] == [
        "bisotun-police-road-trailhead",
        "bisotun-maidan",
        "bisotun",
    ]
    assert route["timing_status"] == "estimated"

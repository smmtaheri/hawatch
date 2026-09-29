import json
from pathlib import Path


def test_bisotun_has_an_indexable_peak_and_hiking_route():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/bisotun_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "bisotun"
    point = catalog["weather_points"]["bisotun"]
    assert point["seo_indexable"] is True
    assert point["name"] == point["page_name"] == point["short_label"] == "قلهٔ بیستون کرمانشاه"
    assert point["place_type"] == "summit"
    assert point["latitude"] == 34.3888819
    trailhead = catalog["weather_points"]["bisotun-mishri-trailhead"]
    assert trailhead["name"] == trailhead["page_name"] == trailhead["short_label"] == "مبدأ مسیر میشه‌ری بیستون"
    assert trailhead["seo_indexable"] is False
    field = catalog["weather_points"]["bisotun-maidan"]
    assert field["name"] == field["page_name"] == field["short_label"] == "دشت میدان بیستون"
    assert field["place_type"] == "meadow"
    route = catalog["routes"]["bisotun_mishri"]
    assert route["slug"] == "bisotun-mishri-summit"
    assert route["points"] == [
        "bisotun-mishri-trailhead",
        "bisotun-maidan",
        "bisotun",
    ]
    assert route["origin"] == "مبدأ مسیر میشه‌ری بیستون"
    assert route["target_label"] == "قلهٔ بیستون کرمانشاه"
    assert route["timing_status"] == "estimated"

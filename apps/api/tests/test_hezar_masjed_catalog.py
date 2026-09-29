import json
from pathlib import Path


def test_hezar_masjed_has_a_named_origin_landmark_and_indexable_summit():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/hezar_masjed_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "hezar-masjed"
    summit = catalog["weather_points"]["hezar-masjed"]
    assert summit["name"] == summit["page_name"] == "قلهٔ هزارمسجد خراسان رضوی"
    assert summit["seo_indexable"] is True
    assert summit["place_type"] == "summit"
    assert summit["latitude"] == 36.9734
    assert summit["longitude"] == 59.3566

    route = catalog["routes"]["hezar_masjed_chaharrah"]
    assert route["slug"] == "hezar-masjed-chaharrah"
    assert route["points"] == [
        "hezar-masjed-chaharrah",
        "hezar-masjed-arab-chah",
        "hezar-masjed",
    ]
    assert route["timing_status"] == "estimated"
    assert route["timing"]["cumulative_minutes"] == {
        "hezar-masjed-chaharrah": 0,
        "hezar-masjed-arab-chah": 90,
        "hezar-masjed": 360,
    }

    assert catalog["weather_points"]["hezar-masjed-chaharrah"]["seo_indexable"] is False
    assert catalog["weather_points"]["hezar-masjed-arab-chah"]["name"] == "دشت عرب‌چاه هزارمسجد"

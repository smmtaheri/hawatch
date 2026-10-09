import json
from pathlib import Path


def test_shirabad_catalog_has_searchable_destinations_and_one_hiking_route():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/shirabad_waterfalls_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    expected_indexable = {
        "shirabad-village",
        "shirabad-waterfall",
        "shirabad-seven-waterfalls",
        "shirabad-div-sepid-cave",
    }
    assert {
        slug for slug, point in catalog["weather_points"].items() if point["seo_indexable"]
    } == expected_indexable

    route = catalog["routes"]["shirabad-seven-waterfalls-trail"]
    assert route["points"][0] == "shirabad-waterfalls-parking"
    assert route["points"][-1] == "shirabad-seven-waterfalls"
    assert "shirabad-waterfall" in route["points"]
    assert "shirabad-div-sepid-cave" in route["points"]
    assert route["distance_km"] == 3.22
    assert route["ascent_m"] == 256
    assert route["timing_status"] == "estimated"
    assert route["one_way_minutes"] == 95
    assert len(route["evidence_tracks"]) == 2
    assert all(path.startswith("tracks/shirabad-waterfalls/") for path in route["evidence_tracks"])


def test_shirabad_route_does_not_turn_vehicle_access_into_hiking_distance():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/shirabad_waterfalls_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))
    route = catalog["routes"]["shirabad-seven-waterfalls-trail"]

    assert route["origin"] == "پارکینگ آبشارهای شیرآباد"
    assert "روستا" not in route["origin"]
    assert catalog["weather_points"]["shirabad-village"]["seo_indexable"] is True
    assert catalog["weather_points"]["shirabad-waterfalls-parking"]["seo_indexable"] is False

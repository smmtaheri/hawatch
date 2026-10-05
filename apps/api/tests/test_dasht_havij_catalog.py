import json
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "fixtures/catalog/rizan_v3.json"


def test_dasht_havij_is_an_independent_indexable_destination():
    catalog = json.loads(CATALOG.read_text())
    point = catalog["weather_points"]["dasht-havij"]
    assert point["name"] == point["page_name"] == point["short_label"] == point["tile_name"] == "دشت هویج"
    assert point["importance"] == point["kind"] == "primary"
    assert point["seo_indexable"] is True
    assert point["place_type"] == point["category_key"] == "meadow"
    assert point["short_category"] == point["category"] == "دشت"
    assert "گرچال" in point["aliases"]
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (35.882463, 51.705332, 2566)
    assert "rizan-hoyej-meadow" not in CATALOG.read_text()


def test_promotion_preserves_existing_route_chains_and_metrics():
    catalog = json.loads(CATALOG.read_text())
    expected = {
        "afjeh-hoyej-rizan": (["rizan-afjeh-trailhead", "dasht-havij", "rizan"], 6.44, 1590),
        "andar-person-rizan": (["rizan-afjeh-trailhead", "dasht-havij", "rizan-andar", "rizan-person", "rizan"], 10.48, 1738),
        "afjeh-hoyej-person": (["rizan-afjeh-trailhead", "dasht-havij", "rizan-andar", "rizan-person"], 6.26, 1103),
    }
    for slug, (points, distance, ascent) in expected.items():
        route = catalog["routes"][slug]
        assert route["points"] == points
        assert route["distance_km"] == distance
        assert route["ascent_m"] == ascent
        assert "dasht-havij" in route["public_point_notes"]
        assert route["timing_status"] == "pending"
        assert route["timing"] is None
    assert len(catalog["routes"]) == 4

import json
from pathlib import Path


def test_loveh_catalog_has_searchable_village_and_waterfall():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/loveh_waterfall_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert {
        slug for slug, point in catalog["weather_points"].items() if point["seo_indexable"]
    } == {"loveh-village", "loveh-waterfall"}
    route = catalog["routes"]["loveh-waterfall-source"]
    assert route["points"] == [
        "loveh-waterfall-trailhead",
        "loveh-waterfall",
        "loveh-waterfall-source",
    ]
    assert route["distance_km"] == 1.37
    assert route["ascent_m"] == 98
    assert route["timing_status"] == "estimated"
    assert route["timing"]["cumulative_minutes"]["loveh-waterfall-source"] == 30


def test_loveh_route_excludes_vehicle_access_from_timing():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/loveh_waterfall_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))
    route = catalog["routes"]["loveh-waterfall-source"]

    assert route["origin"] == "پای کار آبشار لوه"
    assert "روستا" not in route["origin"]
    assert "جاده‌ای روستا" in catalog["weather_points"]["loveh-waterfall-trailhead"]["identity_summary"]

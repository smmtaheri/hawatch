import json
from pathlib import Path


def test_abbasabad_has_one_lake_forest_identity_and_a_complete_hiking_route():
    catalog = json.loads(
        (Path(__file__).parents[1] / "fixtures/catalog/abbasabad_behshahr_v1.json").read_text()
    )
    lake = catalog["weather_points"]["abbasabad-behshahr"]
    assert lake["name"] == lake["page_name"] == catalog["point"]["name"]
    assert lake["seo_indexable"] and lake["kind"] == "primary"
    assert "جنگل عباس آباد" in lake["aliases"]
    assert lake["category_key"] == "lake"
    route = catalog["routes"]["via_narges_tappeh"]
    assert route["points"] == ["narges-tappeh-trailhead", "narges-tappeh", "abbasabad-behshahr"]
    assert catalog["weather_points"]["narges-tappeh"]["seo_indexable"]
    assert not catalog["weather_points"]["narges-tappeh-trailhead"]["seo_indexable"]
    times = [route["timing"]["cumulative_minutes"][slug] for slug in route["points"]]
    assert times == [0, 50, 100]
    assert route["one_way_minutes"] == times[-1]
    assert route["timing_status"] == "estimated"
    assert route["distance_km"] == 4.6 and route["ascent_m"] == 316
    assert len(catalog["weather_points"]) == 3

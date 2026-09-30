import json
from pathlib import Path


def test_varvasht_catalog_exposes_primary_peak_and_harijan_route_chain():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/varvasht_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "varvasht"
    assert catalog["shared_weather_points"] == ["harijan-village"]

    peak = catalog["weather_points"]["varvasht"]
    assert peak["name"] == "قلهٔ وروشت"
    assert peak["place_type"] == "summit"
    assert peak["seo_indexable"] is True

    route = catalog["routes"]["harijan_to_varvasht"]
    assert route["slug"] == "varvasht-harijan"
    assert route["points"] == [
        "harijan-village",
        "varvasht-harijan-dry-valley",
        "varvasht-meadow",
        "varvasht-main-ridge",
        "varvasht",
    ]
    assert route["timing_status"] == "estimated"
    assert route["timing"]["cumulative_minutes"]["varvasht"] == 380

    assert catalog["weather_points"]["varvasht-meadow"]["seo_indexable"] is False

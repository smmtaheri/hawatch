import json
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("key", "duration", "distance", "ascent", "cumulative"),
    [
        ("abbar_to_qaleh_roudkhan", 575, 25.98, 325, [0, 75, 130, 250, 400, 575]),
        ("mazgadeh_to_qaleh_roudkhan", 465, 16.16, 1251, [0, 215, 300, 465]),
    ],
)
def test_qaleh_routes_have_complete_stop_free_one_way_estimates(
    key, duration, distance, ascent, cumulative
):
    catalog = json.loads(
        (Path(__file__).parents[1] / "fixtures/catalog/qaleh_roudkhan_v1.json").read_text()
    )
    route = catalog["routes"][key]
    timing = route["timing"]
    assert route["timing_status"] == "estimated"
    assert route["one_way_minutes"] == duration
    assert route.get("round_trip_minutes") is None
    assert route["distance_km"] == distance
    assert route["ascent_m"] == ascent
    assert set(timing["cumulative_minutes"]) == set(route["points"])
    assert [timing["cumulative_minutes"][slug] for slug in route["points"]] == cumulative
    assert all(a < b for a, b in zip(cumulative, cumulative[1:]))
    assert cumulative[0] == 0 and cumulative[-1] == duration
    assert timing["method"] == "gpx-smoothed-tobler-terrain"
    assert timing["confidence"] == "medium"
    assert timing["uncertainty_minutes"] == 120
    assert len(timing["source_urls"]) == 2
    assert route["points"][-1] == "qaleh-roudkhan"
    assert "qaleh-roudkhan-mte-khani" in route["points"]
    assert all(slug in catalog["weather_points"] for slug in route["points"])

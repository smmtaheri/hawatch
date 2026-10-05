import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1] / "fixtures/catalog"
CASES = [
    ("arakouh_v1.json", "arakouh", 5.82, 210),
    ("araghchin_v1.json", "araghchin", 4.01, 180),
    ("kasonak_v1.json", "kasonak", 6.39, 210),
    ("doshakh_tehran_v1.json", "doshakh-tehran", 6.9, 255),
]


@pytest.mark.parametrize("filename,primary,distance,minutes", CASES)
def test_summit_identity_and_meaningful_outbound_route(filename, primary, distance, minutes):
    c = json.loads((ROOT / filename).read_text())
    from hawatch.modules.catalog.catalog import _validate_document_shape

    _validate_document_shape(c)
    assert c["primary_point"] == c["point"]["slug"] == primary
    p = c["weather_points"][primary]
    assert p["seo_indexable"] and p["kind"] == "primary"
    assert p["place_type"] == "summit"
    for row in c["weather_points"].values():
        assert row["name"] == row["page_name"] == row["short_label"]
        assert row["elevation_m"] > 0 and row["source_urls"]
        assert not any(word in row["name"] for word in ("کمپ", "استراحت"))
        if row["kind"] == "route_point":
            assert row["seo_indexable"] is False
    r = c["routes"]["main"]
    assert len(r["points"]) >= 3 and r["points"][-1] == primary
    assert set(r["points"]) <= set(c["weather_points"]) | set(c["shared_weather_points"])
    times = [r["timing"]["cumulative_minutes"][slug] for slug in r["points"]]
    assert times[0] == 0 and all(a < b for a, b in zip(times, times[1:]))
    assert times[-1] == r["one_way_minutes"] == minutes
    assert r["distance_km"] == distance  # summit-bound leg, not return/continuation
    assert r["timing_status"] == "estimated"
    assert r["timing"]["uncertainty_minutes"] == 45


def test_existing_trailheads_and_kara_junction_are_reused():
    k = json.loads((ROOT / "kasonak_v1.json").read_text())
    d = json.loads((ROOT / "doshakh_tehran_v1.json").read_text())
    assert k["shared_weather_points"] == ["khatun-bargah-trailhead"]
    assert d["shared_weather_points"] == [
        "chin-kalagh-darakeh-trailhead", "palangchal-kara-junction"
    ]
    for c in (k, d):
        assert not set(c["shared_weather_points"]) & set(c["weather_points"])
    p = d["weather_points"]["doshakh-tehran"]
    assert (p["latitude"], p["longitude"], p["elevation_m"]) == (35.847333, 51.361661, 2978)
    assert "دوشاخ جنوبی" in p["aliases"]
    assert d["routes"]["main"]["points"] == [
        "chin-kalagh-darakeh-trailhead", "palangchal-kara-junction",
        "doshakh-shelter", "doshakh-tehran",
    ]

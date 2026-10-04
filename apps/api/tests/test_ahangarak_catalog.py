import json
from pathlib import Path


CATALOG = Path(__file__).resolve().parents[1] / "fixtures/catalog/ahangarak_v1.json"


def test_ahangarak_shared_origin_and_real_intermediates():
    catalog = json.loads(CATALOG.read_text())
    points = catalog["weather_points"]
    assert catalog["primary_point"] == catalog["point"]["slug"] == "ahangarak"
    assert len(catalog["catalog_version"]) <= 32
    assert catalog["shared_weather_points"] == ["ahar-village"]
    assert "ahar-village" not in points
    assert {s for s, p in points.items() if p["seo_indexable"]} == {"ahangarak", "esterchal"}
    assert all(p["name"] == p["page_name"] == p["short_label"] for p in points.values())
    assert all(p["source_urls"] and p["elevation_source"] for p in points.values())
    for route in catalog["routes"].values():
        assert route["points"][1:] == ["esterchal", "esterchal-pass", "ahangarak"]
        assert "dehtangeh-waterfall" not in route["points"]
    assert catalog["routes"]["ahar"]["points"][0] == "ahar-village"
    assert catalog["routes"]["hamlun"]["points"][0] == "hamlun-trailhead"


def test_ahangarak_outbound_metrics_and_complete_timing():
    catalog = json.loads(CATALOG.read_text())
    assert {r["slug"] for r in catalog["routes"].values()} == {"ahangarak-ahar", "ahangarak-hamlun"}
    for route in catalog["routes"].values():
        times = [route["timing"]["cumulative_minutes"][slug] for slug in route["points"]]
        assert times[0] == 0 and times[-1] == route["one_way_minutes"]
        assert all(a < b for a, b in zip(times, times[1:]))
        assert route["timing_status"] == "estimated"
        assert route["timing"]["confidence"] == "medium"
        assert "شرایط خشک" in route["public_note"]
    assert catalog["routes"]["ahar"]["distance_km"] == 11.01
    assert catalog["routes"]["ahar"]["ascent_m"] == 1359
    assert catalog["routes"]["ahar"]["one_way_minutes"] == 345
    assert catalog["routes"]["hamlun"]["distance_km"] == 8.03
    assert catalog["routes"]["hamlun"]["ascent_m"] == 1092
    assert catalog["routes"]["hamlun"]["one_way_minutes"] == 285
    assert "اکتشافی" in catalog["routes"]["ahar"]["public_note"]
    assert "برگشت دست‌به‌سنگ" in catalog["routes"]["hamlun"]["public_note"]
    assert "stitched timestamps NOT used" in catalog["routes"]["hamlun"]["internal_note"]

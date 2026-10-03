import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "fixtures/catalog/janestoon_v1.json"

def test_janestoon_distinct_summits_and_shared_points():
    c = json.loads(CATALOG.read_text())
    p = c["weather_points"]
    assert p["janestoon-east"]["longitude"] != p["janestoon-west"]["longitude"]
    assert all(p[s]["seo_indexable"] and p[s]["kind"] == "primary" for s in ("janestoon-east", "janestoon-west", "biuk-agha-cave"))
    assert not p["janestoon-abnik-trailhead"]["seo_indexable"]
    assert all(s not in p for s in c["shared_weather_points"])
    assert len(c["catalog_version"]) <= 32

def test_janestoon_routes_have_complete_one_way_timing():
    c = json.loads(CATALOG.read_text())
    assert len(c["routes"]) == 3
    for r in c["routes"].values():
        assert len(r["points"]) >= 3
        t = [r["timing"]["cumulative_minutes"][s] for s in r["points"]]
        assert t[0] == 0 and t[-1] == r["one_way_minutes"]
        assert all(a < b for a, b in zip(t, t[1:]))
        assert r["timing_status"] == "estimated"
    assert c["routes"]["lalun"]["points"][-1] == "janestoon-west"
    assert "biuk-agha-cave" not in c["routes"]["west"]["points"]

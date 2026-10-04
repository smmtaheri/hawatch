import json
from pathlib import Path

from hawatch.modules.catalog.identity import metadata_for_point


ROOT = Path(__file__).resolve().parents[1] / "fixtures/catalog"


def test_ahar_promoted_without_duplicate_or_losing_tochal_route():
    t = json.loads((ROOT / "tochal_v1.json").read_text())
    c = json.loads((ROOT / "qaleh_dokhtar_ahar_v1.json").read_text())
    s = "ahar-village"
    p = t["weather_points"][s]
    assert p["name"] == p["page_name"] == p["short_label"] == "روستای آهار"
    assert p["kind"] == p["importance"] == "primary"
    assert p["seo_indexable"] and p["category_key"] == "village"
    identity = metadata_for_point(s, p, is_primary=True)
    assert identity["name"] == identity["page_name"] == identity["short_label"] == "روستای آهار"
    assert s in c["shared_weather_points"] and s not in c["weather_points"]
    r = t["routes"]["ahar_to_tochal"]
    assert r["points"][0] == s and r["timing"]["cumulative_minutes"][s] == 0
    assert r["points"][-1] == "tochal" and r["one_way_minutes"] == 380


def test_qaleh_dokhtar_shared_pass_and_complete_outbound_timings():
    c = json.loads((ROOT / "qaleh_dokhtar_ahar_v1.json").read_text())
    assert len(c["routes"]) == 2 and len(c["catalog_version"]) <= 32
    assert set(c["weather_points"]) == {
        "qaleh-dokhtar-ahar", "zargah-pass", "dehtangeh-waterfall"
    }
    assert not c["weather_points"]["zargah-pass"]["seo_indexable"]
    for r in c["routes"].values():
        assert r["points"][-1] == c["primary_point"]
        assert "zargah-pass" in r["points"] and len(r["points"]) >= 3
        minutes = [r["timing"]["cumulative_minutes"][s] for s in r["points"]]
        assert minutes[0] == 0 and minutes[-1] == r["one_way_minutes"]
        assert all(a < b for a, b in zip(minutes, minutes[1:]))
        assert r["timing_status"] == "estimated"
    assert "dehtangeh-waterfall" in c["routes"]["ahar"]["points"]
    assert c["routes"]["shahrestanak"]["points"][0] == "shahrestanak"
    assert "مرکز روستا" in c["routes"]["shahrestanak"]["public_note"]
    assert c["routes"]["shahrestanak"]["one_way_minutes"] != 162

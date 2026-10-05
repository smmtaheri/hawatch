import json
from pathlib import Path


CATALOG = Path(__file__).resolve().parents[1] / "fixtures/catalog/abak_v1.json"


def test_abak_identity_and_real_intermediates():
    c = json.loads(CATALOG.read_text())
    p = c["weather_points"]
    assert c["primary_point"] == c["point"]["slug"] == "abak"
    assert len(c["catalog_version"]) <= 32
    assert {s for s, r in p.items() if r["seo_indexable"]} == {
        "abak", "pinasum", "fasham", "meygun", "ruteh-village"
    }
    assert all(r["name"] == r["page_name"] == r["short_label"] for r in p.values())
    assert all(r["source_urls"] and r["elevation_source"] for r in p.values())
    assert c["routes"]["north"]["points"] == [
        "abak-shemshak-trailhead", "pinasum", "pinasum-pass", "abak"
    ]
    # The summer bypass must not inherit the gully on the Ruteh ascent.
    assert "abak-gully" not in c["routes"]["southwest"]["points"]
    assert "abak-gully" in c["routes"]["southeast"]["points"]


def test_abak_outbound_timing_and_safety_notes():
    c = json.loads(CATALOG.read_text())
    assert len(c["routes"]) == 3
    for r in c["routes"].values():
        assert r["points"][-1] == "abak" and len(r["points"]) >= 3
        times = [r["timing"]["cumulative_minutes"][s] for s in r["points"]]
        assert times[0] == 0 and times[-1] == r["one_way_minutes"]
        assert all(a < b for a, b in zip(times, times[1:]))
        assert r["timing_status"] == "estimated"
        assert 4 < r["distance_km"] < 7 and 1000 < r["ascent_m"] < 1400
        assert c["weather_points"][r["points"][0]]["seo_indexable"] == (
            r["slug"] != "abak-shemshak"
        )
    assert "شرایط خشک" in c["routes"]["north"]["public_note"]
    assert "دست‌به‌سنگ" in c["routes"]["southeast"]["public_note"]
    assert {r["slug"] for r in c["routes"].values()} == {
        "abak-shemshak", "abak-meygun", "abak-ruteh"
    }

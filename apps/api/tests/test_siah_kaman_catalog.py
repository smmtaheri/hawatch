import json
from pathlib import Path


def test_siah_kaman_catalog_exposes_two_distinct_climbing_routes():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/siah_kaman_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "siah-kaman"
    assert catalog["weather_points"]["siah-kaman"]["seo_indexable"] is True
    assert catalog["shared_weather_points"] == ["alamkuh-vandarbon", "alamkuh-tang-galu"]

    north = catalog["routes"]["vandarbon-siah-kaman"]
    assert north["points"] == ["alamkuh-vandarbon", "siah-kaman-naft-chak", "siah-kaman"]
    assert north["timing"]["cumulative_minutes"] == {
        "alamkuh-vandarbon": 0,
        "siah-kaman-naft-chak": 180,
        "siah-kaman": 420,
    }
    assert north["timing_status"] == "estimated"
    assert north["timing"]["uncertainty_minutes"] == 90

    chalon = catalog["routes"]["tang-galu-siah-kaman-chalon"]
    assert chalon["points"] == ["alamkuh-tang-galu", "siah-kaman-chalon-pass", "siah-kaman"]
    assert chalon["timing"]["cumulative_minutes"] == {
        "alamkuh-tang-galu": 0,
        "siah-kaman-chalon-pass": 300,
        "siah-kaman": 360,
    }
    assert chalon["timing"]["confidence"] == "low"
    assert chalon["timing"]["uncertainty_minutes"] == 120

    for route in (north, chalon):
        assert route["timing"]["cumulative_minutes"][route["points"][-1]] == route["one_way_minutes"]
        assert len(route["evidence_tracks"]) == 1

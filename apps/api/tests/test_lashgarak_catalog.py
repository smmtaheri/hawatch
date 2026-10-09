import json
from pathlib import Path


def test_lashgarak_catalog_has_two_indexable_summits_and_distinct_routes():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/lashgarak_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "lashgarak-bozorg"
    assert catalog["shared_weather_points"] == ["alamkuh-hesarchal"]
    assert catalog["weather_points"]["lashgarak-bozorg"]["seo_indexable"] is True
    assert catalog["weather_points"]["lashgarak-koochak"]["seo_indexable"] is True

    south = catalog["routes"]["parachan-lashgarak-ridge"]
    assert south["points"] == [
        "lashgarak-parachan",
        "lashgarak-damcheh",
        "lashgarak-bozorg",
        "lashgarak-koochak",
    ]
    assert south["timing"]["cumulative_minutes"]["lashgarak-koochak"] == south["one_way_minutes"]
    assert south["timing_status"] == "estimated"

    north = catalog["routes"]["hesarchal-lashgarak-bozorg"]
    assert north["points"] == [
        "alamkuh-hesarchal",
        "lashgarak-north-snowfield",
        "lashgarak-bozorg",
    ]
    assert north["timing"]["cumulative_minutes"]["lashgarak-bozorg"] == north["one_way_minutes"]
    assert north["timing"]["confidence"] == "low"

    for route in (south, north):
        cumulative = list(route["timing"]["cumulative_minutes"].values())
        assert cumulative == sorted(cumulative)
        assert len(route["evidence_tracks"]) == 1

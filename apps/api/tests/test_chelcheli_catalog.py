import json
from pathlib import Path


def test_chelcheli_catalog_exposes_primary_peak_and_named_route_chain():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/chelcheli_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "chelcheli"
    peak = catalog["weather_points"]["chelcheli"]
    assert peak["name"] == "قلهٔ چلچلی"
    assert peak["seo_indexable"] is True
    assert peak["place_type"] == "summit"

    route = catalog["routes"]["chelcheli-cheh-ja-loop"]
    assert route["points"] == [
        "chelcheli-cheh-ja-village",
        "chelcheli-spring",
        "chelcheli",
    ]
    assert route["timing_status"] == "pending"
    assert route["evidence_tracks"] == [
        "tracks/chelcheli/chelcheli-cheh-ja-loop-primary.gpx"
    ]

    spring = catalog["weather_points"]["chelcheli-spring"]
    assert spring["place_type"] == "spring"
    assert spring["seo_indexable"] is False

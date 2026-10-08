import json
from pathlib import Path


def test_arasbaran_cluster_has_independent_destinations_and_babak_hiking_route():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/arasbaran_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["catalog_version"] == "hawatch-arasbaran-cluster-v1"
    assert catalog["primary_point"] == "arasbaran-forest"

    destinations = {
        "arasbaran-forest",
        "ainalu-arasbaran",
        "makidi-forest",
        "babak-castle",
        "kaleybar",
    }
    for slug in destinations:
        row = catalog["weather_points"][slug]
        assert row["kind"] == "primary"
        assert row["importance"] == "primary"
        assert row["seo_indexable"] is True
        assert row["source_urls"]

    castle = catalog["weather_points"]["babak-castle"]
    assert castle["category_key"] == "fort"
    assert "قلعهٔ بابک" in castle["name"]

    access = catalog["weather_points"]["kaleybar"]
    assert access["place_type"] == "city"
    assert access["seo_indexable"] is True

    route = catalog["routes"]["babak-castle-ascent"]
    assert route["points"] == [
        "babak-hotel-trailhead",
        "babak-trail-teahouse",
        "babak-castle",
    ]
    assert route["distance_km"] == 3.43
    assert route["ascent_m"] == 501
    assert route["timing_status"] == "estimated"
    assert route["timing"]["cumulative_minutes"] == {
        "babak-hotel-trailhead": 0,
        "babak-trail-teahouse": 80,
        "babak-castle": 135,
    }

    for slug in ("babak-hotel-trailhead", "babak-trail-teahouse"):
        assert catalog["weather_points"][slug]["seo_indexable"] is False

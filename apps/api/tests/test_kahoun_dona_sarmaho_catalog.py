import json
from pathlib import Path

CATALOG_DIR = Path(__file__).parents[1] / "fixtures/catalog"


def load(name):
    return json.loads((CATALOG_DIR / name).read_text())


def test_kahoun_reuses_deryouk_and_has_complete_timing():
    catalog = load("kahoun_v1.json")
    assert catalog["shared_weather_points"] == ["deryouk-plain"]
    assert "deryouk-plain" not in catalog["weather_points"]
    route = catalog["routes"]["namar"]
    assert len(route["points"]) == 6
    assert route["points"][-1] == "kahoun"
    assert route["one_way_minutes"] == 340
    assert catalog["weather_points"]["lara-plain"]["seo_indexable"]
    assert not catalog["weather_points"]["kahoun-namar-trailhead"]["seo_indexable"]
    assert "namar-village" not in catalog["weather_points"]


def test_dona_has_two_distinct_origins_and_one_summit():
    catalog = load("dona_v1.json")
    assert len(catalog["routes"]) == 2
    north, south = catalog["routes"].values()
    assert north["points"][0] == "dona-olya"
    assert south["points"][0] == "azadkouh-varangerud-start"
    assert north["points"][-1] == south["points"][-1] == "dona"
    assert "azadkouh-varangerud-start" not in catalog["weather_points"]
    assert catalog["weather_points"]["dona-olya"]["place_type"] == "village"
    for route in (north, south):
        times = [route["timing"]["cumulative_minutes"][s] for s in route["points"]]
        assert times[0] == 0
        assert all(a < b for a, b in zip(times, times[1:]))
        assert times[-1] == route["one_way_minutes"]
        assert route["timing_status"] == "estimated"


def test_sarmaho_is_indexable_without_misrepresenting_technical_route():
    catalog = load("sarmaho_v1.json")
    assert catalog["routes"] == {}
    point = catalog["weather_points"]["sarmaho"]
    assert point["seo_indexable"] and point["kind"] == "primary"
    assert point["name"] == point["page_name"] == catalog["point"]["name"]
    for name in ("kahoun_v1.json", "dona_v1.json", "sarmaho_v1.json"):
        assert len(load(name)["catalog_version"]) <= 32

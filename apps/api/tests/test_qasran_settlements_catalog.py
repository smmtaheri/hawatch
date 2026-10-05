import json
from math import asin, cos, radians, sin, sqrt
from pathlib import Path


ROOT = Path(__file__).parents[1] / "fixtures/catalog"


def catalog(name):
    return json.loads((ROOT / name).read_text())


def test_settlements_have_searchable_consistent_identities():
    for filename, slug, name, family in [
        ("abak_v1.json", "fasham", "فشم", "city"),
        ("abak_v1.json", "meygun", "میگون", "city"),
        ("abak_v1.json", "ruteh-village", "روستای روته", "village"),
        ("mehrchal_v1.json", "garmabdar", "روستای گرمابدر", "village"),
        ("rizan_v3.json", "afjeh", "روستای افجه", "village"),
    ]:
        p = catalog(filename)["weather_points"][slug]
        assert p["name"] == p["page_name"] == name
        assert p["short_label"] in (name, "افجه")
        assert p["place_type"] == p["category_key"] == family
        assert p["kind"] == p["importance"] == "primary"
        assert p["seo_indexable"] is True
        assert p["source_urls"] and p["aliases"] and p["elevation_source"]


def test_promoted_origins_keep_coordinates_and_route_timing():
    c = catalog("abak_v1.json")
    for key, slug, coords, name, minutes in [
        ("southwest", "meygun", (35.957207, 51.493653, 2152), "میگون", 285),
        ("southeast", "ruteh-village", (35.962639, 51.543286, 2198), "روستای روته", 330),
    ]:
        p = c["weather_points"][slug]
        r = c["routes"][key]
        assert (p["latitude"], p["longitude"], p["elevation_m"]) == coords
        assert r["points"][0] == slug and r["origin"] == name
        assert r["timing"]["cumulative_minutes"][slug] == 0
        assert r["one_way_minutes"] == minutes
    assert "abak-meygun-trailhead" not in json.dumps(c)
    assert "abak-ruteh-trailhead" not in json.dumps(c)


def test_garmabdar_village_is_not_the_distant_environment_station():
    c = catalog("mehrchal_v1.json")
    p = c["weather_points"]["garmabdar"]
    t = c["weather_points"]["mehrchal-garmabdar-trailhead"]
    assert (p["latitude"], p["longitude"], p["elevation_m"]) == (35.98833, 51.63167, 2455)
    dlat, dlon = radians(t["latitude"] - p["latitude"]), radians(t["longitude"] - p["longitude"])
    distance = 12742000 * asin(sqrt(sin(dlat / 2) ** 2 + cos(radians(p["latitude"])) * cos(radians(t["latitude"])) * sin(dlon / 2) ** 2))
    assert distance > 1000
    assert t["seo_indexable"] is False
    assert c["routes"]["garmabdar-pirzan-mehrchal"]["points"][0] == "mehrchal-garmabdar-trailhead"
    assert all("garmabdar" not in r["points"] for r in c["routes"].values())

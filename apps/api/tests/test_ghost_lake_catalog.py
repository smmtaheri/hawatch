import json
from pathlib import Path


def test_ghost_lake_cluster_has_distinct_indexable_point_only_destinations():
    directory = Path(__file__).parents[1] / "fixtures/catalog"
    catalog = json.loads((directory / "ghost_lake_v1.json").read_text())
    expected = {"ghost-lake", "avidar-lake", "salah-od-din-kola", "chalandar"}
    assert set(catalog["weather_points"]) == expected
    assert catalog["routes"] == {}
    assert catalog["primary_point"] == "ghost-lake"
    assert catalog["weather_points"]["ghost-lake"]["category_key"] == "marsh"
    assert catalog["point"]["category_key"] == "marsh"
    assert "دریاچه ممرز" in catalog["weather_points"]["ghost-lake"]["aliases"]
    assert catalog["weather_points"]["avidar-lake"]["category_key"] == "dam"
    assert catalog["weather_points"]["salah-od-din-kola"]["elevation_m"] == -21
    for slug, point in catalog["weather_points"].items():
        assert point["seo_indexable"] is True
        assert point["kind"] == point["importance"] == "primary"
        assert point["source_urls"] and point["elevation_source"]
        if point["place_type"] == "village":
            assert point["category_key"] == "village"
        owners = [
            path.name for path in directory.glob("*.json")
            if slug in json.loads(path.read_text()).get("weather_points", {})
        ]
        assert owners == ["ghost_lake_v1.json"]

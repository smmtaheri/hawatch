import json
from pathlib import Path

import pytest

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOG_DIR = Path(__file__).parents[1] / "fixtures" / "catalog"
FILES = ("aseman_sara_v1.json", "nil_kuh_v1.json", "beliran_v1.json", "farakhin_darno_v1.json")


def load(filename):
    return json.loads((CATALOG_DIR / filename).read_text())


@pytest.mark.parametrize("filename", FILES)
def test_forest_cluster_identity_and_complete_estimated_route_timing(filename):
    catalog = load(filename)
    assert not validate_catalog_document(catalog)
    assert len(catalog["catalog_version"]) <= 32
    assert not catalog["point"]["is_popular"]
    for point in catalog["weather_points"].values():
        assert point["name"] == point["page_name"]
        assert len(point["name"]) <= 80
        assert len(point["identity_summary"]) <= 255
        assert len(point["elevation_source"]) <= 255
        assert "DEM" in point["elevation_source"]
        assert point["kind"] == ("primary" if point["seo_indexable"] else "route_point")
        assert point["routes"] == {}
    for route in catalog["routes"].values():
        assert len(route["points"]) >= 3
        assert route["timing_status"] == "estimated"
        cumulative = route["timing"]["cumulative_minutes"]
        assert set(cumulative) == set(route["points"])
        times = [cumulative[slug] for slug in route["points"]]
        assert times[0] == 0
        assert all(a < b for a, b in zip(times, times[1:]))
        assert times[-1] == route["one_way_minutes"]
        assert "round_trip_minutes" not in route
        assert route["distance_km"] > 0 and route["ascent_m"] > 0
        assert route["timing"]["uncertainty_minutes"] >= 45


def test_aseman_sara_cuts_at_summit_and_keeps_distant_galdian_separate():
    catalog = load("aseman_sara_v1.json")
    points = catalog["weather_points"]
    for route in catalog["routes"].values():
        assert route["points"][-1] == "aseman-sara"
        assert "aseman-sara-upper-pond" in route["points"][1:-1]
        assert route["distance_km"] < 8
    assert not points["galdian-pond"]["seo_indexable"]
    assert not points["aseman-sara-upper-pond"]["seo_indexable"]
    assert points["galdian"]["seo_indexable"]
    assert not points["aseman-sara-galdian-trailhead"]["seo_indexable"]
    assert points["galdian"]["latitude"] != points["aseman-sara-galdian-trailhead"]["latitude"]
    assert "harzevil-village" not in points


def test_nil_kuh_marsh_is_before_summit_from_tarajiq_but_after_from_pasang():
    catalog = load("nil_kuh_v1.json")
    assert catalog["routes"]["nil-kuh-tarajiq"]["points"] == ["tarajiq", "nil-kuh-marsh", "nil-kuh"]
    assert catalog["routes"]["nil-kuh-pasang-tarajiq"]["points"] == ["pasang-bala", "nil-kuh", "nil-kuh-marsh", "tarajiq"]
    marsh = catalog["weather_points"]["nil-kuh-marsh"]
    assert marsh["category_key"] == "marsh" and marsh["seo_indexable"]
    assert catalog["routes"]["nil-kuh-pasang-tarajiq"]["one_way_minutes"] == 420


def test_beliran_routes_have_real_hot_springs_and_distinct_forest_and_village():
    catalog = load("beliran_v1.json")
    points = catalog["weather_points"]
    assert points["beliran"]["place_type"] == "village"
    assert points["beliran-forest"]["place_type"] == "forest"
    assert points["beliran-hot-spring"]["category_key"] == "hot_spring"
    assert not points["beliran-do-sang-spring"]["seo_indexable"]
    assert catalog["routes"]["beliran-narenjestan"]["points"] == [
        "narenjestan-haraz-bridge", "beliran-do-sang-spring", "beliran-hot-spring", "beliran-forest", "beliran",
    ]
    reverse = catalog["routes"]["beliran-hot-spring-walk"]
    assert reverse["points"] == ["beliran", "beliran-forest", "beliran-hot-spring"]
    assert reverse["distance_km"] == 4.61
    assert "gro" not in points


def test_farakhin_and_darno_do_not_publish_driving_or_rope_access_as_hiking():
    catalog = load("farakhin_darno_v1.json")
    assert catalog["routes"] == {}
    assert set(catalog["weather_points"]) == {"farakhin", "darno", "veysar-mazandaran", "dalasm"}
    assert all(point["seo_indexable"] for point in catalog["weather_points"].values())
    assert "طناب" in catalog["weather_points"]["darno"]["seo"]["description"]
    assert catalog["weather_points"]["darno"]["place_type"] == "waterfall"
    assert catalog["weather_points"]["farakhin"]["elevation_m"] == 819

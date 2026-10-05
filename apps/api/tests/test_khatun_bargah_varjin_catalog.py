import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "fixtures/catalog"


@pytest.mark.parametrize("filename,indexable,route_count", [
    ("khatun_bargah_v1.json", {"khatun-bargah"}, 1),
    ("varjin_v1.json", {"varjin-peak", "kalugan-village"}, 3),
])
def test_new_summit_identity_indexability_and_model_limits(filename, indexable, route_count):
    catalog = json.loads((ROOT / filename).read_text())
    points = catalog["weather_points"]
    assert catalog["primary_point"] == catalog["point"]["slug"]
    assert len(catalog["catalog_version"]) <= 32
    assert len(catalog["routes"]) == route_count
    assert {slug for slug, row in points.items() if row["seo_indexable"]} == indexable
    for row in points.values():
        assert row["name"] == row["page_name"] == row["short_label"]
        assert row["source_urls"] and "GLO-90" in row["elevation_source"]
        assert row["status"] == "provisional"
        for key, limit in {"name": 80, "page_name": 160, "short_label": 80,
                           "region": 64, "identity_summary": 255, "elevation_source": 255}.items():
            assert len(row[key]) <= limit
    for route in catalog["routes"].values():
        assert len(route["points"]) >= 3
        assert route["points"][-1] == catalog["primary_point"]
        assert route["timing_status"] == "estimated"
        times = [route["timing"]["cumulative_minutes"][slug] for slug in route["points"]]
        assert times[0] == 0 and times[-1] == route["one_way_minutes"]
        assert all(a < b for a, b in zip(times, times[1:]))
        assert route["timing"]["source_urls"]
        assert "شرایط خشک" in route["public_note"]


def test_khatun_bargah_excludes_road_and_technical_ridge():
    catalog = json.loads((ROOT / "khatun_bargah_v1.json").read_text())
    route = catalog["routes"]["garmabdar"]
    assert (route["distance_km"], route["ascent_m"], route["one_way_minutes"]) == (4.70, 1021, 210)
    assert route["points"] == ["khatun-bargah-trailhead", "khatun-bargah-south-spring",
                               "khatun-bargah-stone-shelter", "khatun-bargah"]
    assert "indices488..1356" in route["internal_note"]
    assert "3.77km road" in route["internal_note"]
    assert "اشتر" in route["public_note"]
    assert catalog["weather_points"]["khatun-bargah"]["elevation_m"] == 3820


def test_varjin_shared_pass_and_honest_lavasan_direction():
    catalog = json.loads((ROOT / "varjin_v1.json").read_text())
    routes = catalog["routes"]
    assert routes["kalugan"]["points"][0] == "kalugan-village"
    assert routes["kalugan"]["points"][1] == routes["rahatabad"]["points"][1] == "varjin-north-pass"
    assert not catalog["weather_points"]["varjin-north-pass"]["seo_indexable"]
    assert catalog["weather_points"]["kalugan-village"]["place_type"] == "village"
    assert routes["lavasan"]["points"][1] == "varjin-south-cairn"
    assert "NOT on original outbound" in routes["lavasan"]["internal_note"]
    assert "do not use descent timestamps" in routes["lavasan"]["internal_note"]
    assert "شاخهٔ رفت" in routes["lavasan"]["public_note"]
    for key, expected in {"lavasan": (5.80, 1150, 225), "kalugan": (6.60, 1209, 240),
                           "rahatabad": (6.31, 658, 195)}.items():
        route = routes[key]
        assert (route["distance_km"], route["ascent_m"], route["one_way_minutes"]) == expected
    assert catalog["weather_points"]["varjin-peak"]["elevation_m"] == 2945

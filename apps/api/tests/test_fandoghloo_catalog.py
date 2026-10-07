import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOG = json.loads(
    (Path(__file__).parents[1] / "fixtures/catalog/fandoghloo_v1.json").read_text()
)


def test_fandoghloo_identity_and_catalog_contract():
    assert not validate_catalog_document(CATALOG)
    assert CATALOG["primary_point"] == "fandoghloo-namin"
    assert len(CATALOG["weather_points"]) == 13
    for point in CATALOG["weather_points"].values():
        assert point["name"] == point["page_name"] == point["short_label"]
        assert len(point["name"]) <= 80
        assert len(point["region"]) <= 64
        assert len(point["elevation_source"]) <= 255
        assert "DEM" in point["elevation_source"]
        assert point["routes"] == {}
        assert point["kind"] == ("primary" if point["seo_indexable"] else "route_point")


def test_fandoghloo_routes_have_real_intermediates_and_complete_moving_eta():
    assert len(CATALOG["routes"]) == 3
    for route in CATALOG["routes"].values():
        assert len(route["points"]) >= 3
        assert route["timing_status"] == "estimated"
        cumulative = route["timing"]["cumulative_minutes"]
        assert set(cumulative) == set(route["points"])
        times = [cumulative[slug] for slug in route["points"]]
        assert times[0] == 0
        assert all(a < b for a, b in zip(times, times[1:]))
        assert times[-1] == route["one_way_minutes"]
        assert route["distance_km"] > 0 and route["ascent_m"] > 0
        assert "round_trip_minutes" not in route
        assert "fandoghloo-namin" not in route["points"]
        assert all("استراحت" not in CATALOG["weather_points"][slug]["name"] for slug in route["points"])


def test_fandoghloo_trims_driving_and_reuses_shared_walking_points():
    long = CATALOG["routes"]["mehdi-posti-meshe-suyi-giladeh"]
    short = CATALOG["routes"]["giladeh-meshe-suyi"]
    assert long["points"][0] == "mehdi-posti"
    assert long["distance_km"] == 14.56
    assert "خودرو" in long["timing"]["notes"][0]
    assert short["points"] == list(reversed(long["points"][-3:]))
    assert short["distance_km"] == 5.7
    assert short["ascent_m"] > long["ascent_m"]
    assert CATALOG["weather_points"]["meshe-suyi"]["category_key"] == "hot_spring"
    assert "آبگرم علی‌داشی" in CATALOG["weather_points"]["meshe-suyi"]["aliases"]


def test_fandoghloo_villages_cities_and_distant_access_points_stay_distinct():
    points = CATALOG["weather_points"]
    for slug in ("namin", "abi-beyglu"):
        assert points[slug]["place_type"] == points[slug]["category_key"] == "city"
        assert points[slug]["seo_indexable"]
    for village, access in (("giladeh", "giladeh-trailhead"), ("abi-beyglu", "abi-beyglu-forest-trailhead")):
        assert points[village]["latitude"] != points[access]["latitude"]
        assert points[village]["seo_indexable"]
        assert not points[access]["seo_indexable"]
    assert sum(point["seo_indexable"] for point in points.values()) == 9
    assert CATALOG["routes"]["giladeh-telli-bolagh-abi-beyglu"]["points"][-1] == "abi-beyglu-forest-trailhead"

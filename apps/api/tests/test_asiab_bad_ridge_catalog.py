import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOG = Path(__file__).parents[1] / "fixtures/catalog/asiab_bad_ridge_v1.json"


def test_ridge_has_five_independent_peaks_and_no_duplicate_shelter():
    catalog = json.loads(CATALOG.read_text())
    assert not validate_catalog_document(catalog)
    points = catalog["weather_points"]
    assert {slug for slug, row in points.items() if row["seo_indexable"]} == {
        "asiab-bad", "latmal-peak", "heryas-peak", "vardij-peak", "yash"
    }
    assert catalog["point"]["slug"] == catalog["primary_point"] == "asiab-bad"
    assert catalog["point"]["is_popular"] is False
    for row in points.values():
        assert row["name"] == row["page_name"] == row["short_label"]
        assert len(row["name"]) <= 80
        assert len(row["identity_summary"]) <= 255
        assert len(row["elevation_source"]) <= 255
        assert row["source_urls"] and row["elevation_source"]
        if row["seo_indexable"]:
            assert row["place_type"] == "summit"
            assert row["kind"] == row["importance"] == "primary"
    summit, shelter = points["asiab-bad"], points["asiab-bad-omid-shelter"]
    assert summit["longitude"] < shelter["longitude"]
    assert summit["elevation_m"] == 2270
    assert shelter["place_type"] == "shelter"
    assert catalog["reviewed_nearby_point_pairs"][0]["slugs"] == [
        "asiab-bad", "asiab-bad-omid-shelter"
    ]


def test_routes_use_outbound_cuts_real_landmarks_and_stop_free_estimates():
    catalog = json.loads(CATALOG.read_text())
    routes = catalog["routes"]
    assert len(routes) == 5
    assert routes["park_summit"]["points"] == [
        "latmal-park-entrance", "asiab-bad-omid-shelter", "asiab-bad"
    ]
    assert routes["park_ridge"]["points"][-2:] == ["latmal-peak", "heryas-peak"]
    assert routes["park_ridge"]["distance_km"] == 6.0  # not the complete 12.28km loop
    assert routes["park_ridge"]["one_way_minutes"] == 225  # breakfast/return omitted
    assert "return index108" in routes["park_ridge"]["internal_note"]
    assert routes["west_summit"]["distance_km"] == 7.84
    assert routes["west_ridge"]["points"][-1] == "heryas-peak"
    assert routes["west_ridge"]["distance_km"] == 9.28  # before the unsafe post-Heryas branch
    assert "Synthetic40s timestamps rejected" in routes["west_ridge"]["internal_note"]
    assert routes["north"]["points"] == [
        "heryas-valley-trailhead", "heryas-valley-garden", "asiab-bad-omid-shelter", "asiab-bad"
    ]
    assert "Garden matched on ASCENT index42" in routes["north"]["internal_note"]
    assert "مبدأ کنار جادهٔ امامزاده‌داوود است، نه داخل آزادراه" in routes["north"]["public_note"]
    assert all("yash" not in route["points"] for route in routes.values())
    assert "دسترسی آزاد آن تأیید نشده" in catalog["weather_points"]["yash"]["identity_summary"]
    for route in routes.values():
        assert len(route["points"]) >= 3
        assert route["timing_status"] == "estimated"
        assert route["distance_km"] > 0 and route["ascent_m"] > 0
        assert route["target_label"] == catalog["weather_points"][route["points"][-1]]["name"]
        timing = route["timing"]
        minutes = [timing["cumulative_minutes"][slug] for slug in route["points"]]
        assert minutes[0] == 0
        assert minutes[-1] == route["one_way_minutes"]
        assert all(a < b for a, b in zip(minutes, minutes[1:]))
        assert timing["source_urls"] and timing["uncertainty_minutes"] > 0
        assert all("camp" not in slug for slug in route["points"])

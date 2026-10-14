import json
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "fixtures" / "catalog" / "azadkouh_v1.json"


def test_sotak_bozorg_has_main_varangeh_rud_hiking_route():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    point = catalog["weather_points"]["sotak-bozorg"]
    route = catalog["routes"]["sotak_bozorg_from_varangeh_rud"]

    assert catalog["catalog_version"] == "hawatch-azadkouh-catalog-v8"
    assert point["name"] == "قلهٔ سوتک بزرگ"
    assert point["place_type"] == "summit"
    assert point["category_key"] == "mountain"
    assert point["kind"] == "primary"
    assert point["importance"] == "primary"
    assert point["seo_indexable"] is True
    assert "سوتک بزرگ" in point["aliases"]
    assert route["slug"] == "sotak-bozorg-varangeh-rud"
    assert route["points"] == [
        "varangeh-rud",
        "sotak-ascent-ridge",
        "sotak-bozorg",
    ]
    assert route["timing_status"] == "estimated"
    assert route["timing"]["cumulative_minutes"]["sotak-bozorg"] == route["one_way_minutes"]


def test_sotak_route_uses_a_real_non_indexable_ridge_landmark():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    ridge = catalog["weather_points"]["sotak-ascent-ridge"]

    assert ridge["name"] == "یال صعود سوتک"
    assert ridge["place_type"] == "ridge"
    assert ridge["seo_indexable"] is False
    assert ridge["source_urls"]


def test_azadkouh_route_points_have_canonical_names_and_indexable_destinations():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    points = catalog["weather_points"]

    expected_routes = {
        "kelakbala_to_azadkouh": [
            "kelak-bala-baladeh", "kelak-camp-1", "kelak-spring", "kelak-camp-3", "choren-pass", "azadkouh",
        ],
        "varangerud_to_azadkouh": [
            "varangeh-rud", "sotak-pass", "kamankouh-lake", "choren-pass", "azadkouh",
        ],
        "nesen_to_azadkouh": ["nesen", "choren-pass", "azadkouh"],
        "nahiyeh_to_azadkouh": ["nahiyeh-baladeh", "choren-pass", "azadkouh"],
    }
    for key, point_slugs in expected_routes.items():
        route = catalog["routes"][key]
        assert route["points"] == point_slugs
        assert set(route["timing"]["cumulative_minutes"]) == set(point_slugs)
        minutes = [route["timing"]["cumulative_minutes"][slug] for slug in point_slugs]
        assert minutes[0] == 0
        assert minutes[-1] == route["one_way_minutes"]
        assert all(first < second for first, second in zip(minutes, minutes[1:]))
        assert all(slug in points for slug in point_slugs)

    independent_destinations = {
        "kelak-bala-baladeh", "nahiyeh-baladeh", "nesen", "varangeh-rud", "kamankouh-lake",
    }
    assert points["azadkouh"]["short_label"] == "آزادکوه"
    for slug in independent_destinations:
        point = points[slug]
        assert point["kind"] == "primary"
        assert point["importance"] == "primary"
        assert point["seo_indexable"] is True
        assert point["source_urls"]

    assert points["choren-pass"]["seo_indexable"] is True
    assert points["sotak-pass"]["seo_indexable"] is True
    assert points["kelak-camp-1"]["seo_indexable"] is False
    assert points["kelak-spring"]["seo_indexable"] is False
    assert points["kelak-camp-3"]["seo_indexable"] is False


def test_route_descent_overlay_uses_the_same_canonical_azadkouh_points():
    overlay_path = Path(__file__).parents[1] / "fixtures" / "route_descent_v1.json"
    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    routes = {route["slug"]: route for route in overlay["routes"]}
    for route in [
        "azadkouh-kelak-bala", "azadkouh-varangerud", "azadkouh-nesen", "azadkouh-nahiyeh",
    ]:
        assert route in routes
        assert not any(slug.startswith("azadkouh-") for slug in routes[route]["chain"] if slug != "azadkouh")

import json
from pathlib import Path


def test_north_tehran_catalog_uses_public_names_and_estimated_timings():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/north_tehran_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "golabdarreh-park"
    assert catalog["point"]["slug"] == "golabdarreh-park"
    assert catalog["weather_points"]["shervin-shelter"]["page_name"] == "جان‌پناه شروین تهران"
    assert catalog["weather_points"]["kamachal-tehran"]["page_name"] == "قلهٔ کماچال تهران"
    assert catalog["weather_points"]["shahneshin-tehran"]["page_name"] == "قلهٔ شاه‌نشین تهران"

    expected_routes = {
        "golabdarreh_to_espilat": ("golabdarreh-espilat", 300),
        "sarband_to_shervin": ("sarband-shervin", 180),
        "velenjak_to_kamachal": ("velenjak-kamachal", 180),
        "imamzadeh_davoud_to_shahneshin": ("imamzadeh-davoud-shahneshin", 450),
        "station7_to_shahneshin": ("station-7-shahneshin", 55),
    }

    for key, (slug, one_way) in expected_routes.items():
        route = catalog["routes"][key]
        assert route["slug"] == slug
        assert route["timing_status"] == "estimated"
        assert route["one_way_minutes"] == one_way
        cumulative = route["timing"]["cumulative_minutes"]
        assert list(cumulative) == route["points"]
        assert list(cumulative.values())[0] == 0
        assert list(cumulative.values())[-1] == one_way
        assert list(cumulative.values()) == sorted(cumulative.values())

    assert "tochal-golabdarreh-espilat" not in {
        route["slug"] for route in catalog["routes"].values()
    }

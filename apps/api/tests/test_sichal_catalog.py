import json
from pathlib import Path


CATALOG = Path(__file__).resolve().parents[1] / "fixtures/catalog/sichal_v1.json"


def test_sichal_identity_shared_origin_and_real_intermediates():
    catalog = json.loads(CATALOG.read_text())
    points = catalog["weather_points"]
    assert catalog["primary_point"] == catalog["point"]["slug"] == "sichal"
    assert len(catalog["catalog_version"]) <= 32
    assert catalog["shared_weather_points"] == ["ahar-village"]
    assert "ahar-village" not in points
    assert {s for s, p in points.items() if p["seo_indexable"]} == {"sichal", "darbandsar"}
    assert all(p["name"] == p["page_name"] == p["short_label"] for p in points.values())
    assert all(p["source_urls"] and p["elevation_source"] for p in points.values())
    for point in points.values():
        for field, limit in {"name": 80, "page_name": 160, "short_label": 80, "region": 64, "identity_summary": 255, "elevation_source": 255}.items():
            assert len(point[field]) <= limit
    assert points["darbandsar"]["place_type"] == points["darbandsar"]["category_key"] == "neighborhood"
    assert catalog["routes"]["ahar"]["points"] == ["ahar-village", "dehtangeh-upper-waterfall", "sichal"]
    assert catalog["routes"]["dizin"]["points"] == ["sichal-dizin-trailhead", "dizin-upper-cable-car-station", "sichal"]
    assert catalog["routes"]["darbandsar"]["points"] == ["darbandsar", "sichal-east-seasonal-pond", "sichal"]
    for route in catalog["routes"].values():
        assert "dehtangeh-waterfall" not in route["points"]
        assert "darbandsar-ski-resort" not in route["points"]
        assert "kolon-bastak-telecom-tower-trailhead" not in route["points"]


def test_sichal_outbound_metrics_and_complete_estimated_timing():
    catalog = json.loads(CATALOG.read_text())
    expected = {"dizin": (3.08, 392, 120), "darbandsar": (6.53, 1082, 315), "ahar": (12.44, 1582, 390)}
    for key, route in catalog["routes"].items():
        assert (route["distance_km"], route["ascent_m"], route["one_way_minutes"]) == expected[key]
        times = [route["timing"]["cumulative_minutes"][s] for s in route["points"]]
        assert times[0] == 0 and times[-1] == route["one_way_minutes"]
        assert all(a < b for a, b in zip(times, times[1:]))
        assert route["timing_status"] == "estimated"
        assert route["timing"]["source_urls"]
        assert "شرایط خشک" in route["public_note"]
    assert "GPS drift" in catalog["routes"]["ahar"]["internal_note"]
    assert "omit1551..1734" in catalog["routes"]["ahar"]["internal_note"]
    assert "فنی الله‌بند" in catalog["routes"]["ahar"]["public_note"]
    assert "چشمه‌های مسیر برگشت" in catalog["routes"]["darbandsar"]["public_note"]

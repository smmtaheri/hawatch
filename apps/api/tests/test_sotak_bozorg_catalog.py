import json
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "fixtures" / "catalog" / "azadkouh_v1.json"


def test_sotak_bozorg_has_main_varangeh_rud_hiking_route():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    point = catalog["weather_points"]["sotak-bozorg"]
    route = catalog["routes"]["sotak_bozorg_from_varangeh_rud"]

    assert catalog["catalog_version"] == "hawatch-azadkouh-catalog-v7"
    assert point["name"] == "قلهٔ سوتک بزرگ"
    assert point["place_type"] == "summit"
    assert point["category_key"] == "mountain"
    assert point["kind"] == "primary"
    assert point["importance"] == "primary"
    assert point["seo_indexable"] is True
    assert "سوتک بزرگ" in point["aliases"]
    assert route["slug"] == "sotak-bozorg-varangeh-rud"
    assert route["points"] == [
        "azadkouh-varangerud-start",
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

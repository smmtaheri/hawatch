import json
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "fixtures" / "catalog" / "azadkouh_v1.json"


def test_sotak_bozorg_is_an_indexable_independent_summit_without_route():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    point = catalog["weather_points"]["sotak-bozorg"]

    assert catalog["catalog_version"] == "hawatch-azadkouh-catalog-v6"
    assert point["name"] == "قلهٔ سوتک بزرگ"
    assert point["place_type"] == "summit"
    assert point["category_key"] == "mountain"
    assert point["kind"] == "primary"
    assert point["importance"] == "primary"
    assert point["seo_indexable"] is True
    assert "سوتک بزرگ" in point["aliases"]
    assert not any("sotak-bozorg" in route.get("points", []) for route in catalog["routes"].values())

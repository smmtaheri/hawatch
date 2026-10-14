import json
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "fixtures" / "catalog" / "alamkuh_v1.json"


def test_tang_galu_has_a_canonical_indexable_point_page():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    point = catalog["weather_points"]["alamkuh-tang-galu"]

    assert catalog["catalog_version"] == "hawatch-alamkuh-catalog-v5"
    assert point["name"] == "تنگ‌گلو علم‌کوه"
    assert point["page_name"] == "تنگ‌گلو علم‌کوه"
    assert point["short_label"] == "تنگ گلو"
    assert point["place_type"] == "trailhead"
    assert point["seo_indexable"] is True
    assert point["source_urls"]

    route = catalog["routes"]["southern_hesarchal"]
    assert route["points"][0] == "alamkuh-tang-galu"

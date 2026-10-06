import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOG = Path(__file__).parents[1] / "fixtures/catalog/biji_kuh_v1.json"


def test_biji_kuh_identity_and_documented_western_ascent():
    catalog = json.loads(CATALOG.read_text())
    assert not validate_catalog_document(catalog)
    assert catalog["primary_point"] == catalog["point"]["slug"] == "biji-kuh"
    points = catalog["weather_points"]
    assert {slug for slug, row in points.items() if row["seo_indexable"]} == {"biji-kuh"}
    assert points["biji-kuh"]["kind"] == points["biji-kuh"]["importance"] == "primary"
    assert points["biji-kuh"]["category_key"] == "mountain"
    assert all(row["name"] == row["page_name"] == row["short_label"] for row in points.values())
    assert all(row["source_urls"] and row["elevation_source"] for row in points.values())
    assert catalog["point"]["name"] == points["biji-kuh"]["name"] == "قلهٔ بیجی‌کوه"
    assert len(catalog["routes"]) == 1
    route = catalog["routes"]["west"]
    assert route["points"] == ["karaj-mountaineers-square", "biji-kuh-spring", "biji-kuh"]
    assert route["distance_km"] == 2.76  # outbound, not the 6.95km loop
    assert route["ascent_m"] == 590
    assert route["timing_status"] == "estimated"
    assert [route["timing"]["cumulative_minutes"][slug] for slug in route["points"]] == [0, 35, 105]
    assert route["one_way_minutes"] == 105
    assert "synthetic timestamps" in route["internal_note"]
    assert "یال شرقی جزو این مسیر نیست" in route["public_note"]

import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOG = Path(__file__).parents[1] / "fixtures/catalog/sekeh_no_v1.json"


def test_sekeh_no_identity_and_meaningful_hiking_routes():
    catalog = json.loads(CATALOG.read_text())
    assert not validate_catalog_document(catalog)
    assert catalog["primary_point"] == catalog["point"]["slug"] == "sekeh-no"
    points = catalog["weather_points"]
    assert {slug for slug, row in points.items() if row["seo_indexable"]} == {
        "sekeh-no", "sehchal", "velayat-rud"
    }
    assert points["sehchal"]["place_type"] == "summit"
    assert points["velayat-rud"]["place_type"] == "village"
    assert catalog["point"]["name"] == points["sekeh-no"]["name"] == "قلهٔ سکه‌نو"
    assert all(row["name"] == row["page_name"] == row["short_label"] for row in points.values())
    assert all(row["source_urls"] and row["elevation_source"] for row in points.values())
    west = catalog["routes"]["west"]
    assert west["points"] == ["varangeh-rud-tower", "sekeh-no-west-sheepfold", "sekeh-no"]
    assert west["distance_km"] == 6.45
    assert west["ascent_m"] == 1345
    assert "azadkouh-varangerud-start" not in west["points"]
    ridge = catalog["routes"]["velayat_rud_ridge"]
    assert ridge["points"] == ["velayat-rud", "sekeh-no", "sehchal"]
    assert ridge["target_label"] == points["sehchal"]["name"]
    assert ridge["distance_km"] == 7.79  # ascent/traverse, not the 14.2km loop
    assert ridge["ascent_m"] == 1560
    assert list(ridge["timing"]["cumulative_minutes"].values()) == [0, 330, 405]
    assert "فرود از چال‌گردن" in ridge["public_note"]
    assert "direct Velayat->Seke route remains unpublished" in ridge["internal_note"]
    for route in catalog["routes"].values():
        assert len(route["points"]) >= 3
        assert route["timing_status"] == "estimated"
        minutes = [route["timing"]["cumulative_minutes"][slug] for slug in route["points"]]
        assert minutes[0] == 0
        assert minutes[-1] == route["one_way_minutes"]
        assert all(a < b for a, b in zip(minutes, minutes[1:]))
        assert not any("spring" in slug or "camp" in slug for slug in route["points"])

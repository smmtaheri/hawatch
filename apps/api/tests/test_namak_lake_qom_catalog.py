import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOG = Path(__file__).parents[1] / "fixtures/catalog/namak_lake_qom_v1.json"


def test_namak_lake_is_distinct_from_hoz_soltan_and_haj_ali_gholi():
    catalog = json.loads(CATALOG.read_text())
    assert not validate_catalog_document(catalog)
    assert catalog["primary_point"] == "namak-lake-qom"
    assert catalog["routes"] == {}
    point = catalog["weather_points"]["namak-lake-qom"]
    assert point["name"] == point["page_name"] == "دریاچهٔ نمک قم"
    assert point["kind"] == point["importance"] == "primary"
    assert point["seo_indexable"] is True
    assert point["category_key"] == catalog["point"]["category_key"] == "lake"
    assert point["place_type"] == "lake"
    assert point["latitude"] == catalog["point"]["latitude"] == 34.32705
    assert point["longitude"] == catalog["point"]["longitude"] == 51.88337
    assert "حوض سلطان" not in point["aliases"]
    assert "دریاچه نمک حاج علی قلی" not in point["aliases"]
    assert point["source_urls"] and point["elevation_source"]

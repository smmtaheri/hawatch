import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


def test_ovan_lake_is_an_indexable_destination_distinct_from_ovan_village():
    path = Path(__file__).parents[1] / "fixtures/catalog/ovan_lake_v1.json"
    catalog = json.loads(path.read_text())
    assert not validate_catalog_document(catalog)
    slug = catalog["primary_point"]
    lake = catalog["weather_points"][slug]
    assert slug == catalog["point"]["slug"] == "ovan-lake"
    assert lake["name"] == lake["page_name"] == lake["short_label"] == catalog["point"]["name"] == "دریاچهٔ اوان"
    assert lake["kind"] == lake["importance"] == "primary"
    assert lake["seo_indexable"] is True
    assert lake["place_type"] == lake["category_key"] == catalog["point"]["category_key"] == "lake"
    assert "دریاچه آوان" in lake["aliases"]
    assert lake["source_urls"] and lake["elevation_source"]
    assert (lake["latitude"], lake["longitude"], lake["elevation_m"]) == (36.48313, 50.44379, 1793)
    assert catalog["routes"] == {}
    assert catalog["point"]["is_popular"] is False

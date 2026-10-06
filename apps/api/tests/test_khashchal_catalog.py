import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


def test_khashchal_is_indexable_without_importing_a_failed_provider_point():
    path = Path(__file__).parents[1] / "fixtures/catalog/khashchal_v1.json"
    catalog = json.loads(path.read_text())
    assert not validate_catalog_document(catalog)
    summit = catalog["weather_points"]["khashchal"]
    assert summit["name"] == summit["page_name"] == summit["short_label"] == catalog["point"]["name"] == "قلهٔ خشچال"
    assert summit["kind"] == summit["importance"] == "primary"
    assert summit["seo_indexable"] is True
    assert summit["elevation_m"] == catalog["point"]["elevation_m"] == 3896
    assert summit["place_type"] == "summit"
    assert summit["category_key"] == catalog["point"]["category_key"] == "mountain"
    assert set(catalog["weather_points"]) == {"khashchal"}
    assert catalog["routes"] == {}
    assert not catalog.get("shared_weather_points")
    assert summit["source_urls"] and summit["elevation_source"]

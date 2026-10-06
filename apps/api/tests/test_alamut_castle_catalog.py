import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


def test_alamut_castle_is_an_independent_indexable_fort_without_invented_route():
    path = Path(__file__).parents[1] / "fixtures/catalog/alamut_castle_v1.json"
    catalog = json.loads(path.read_text())
    assert not validate_catalog_document(catalog)
    slug = catalog["primary_point"]
    point = catalog["weather_points"][slug]
    assert slug == catalog["point"]["slug"] == "alamut-castle"
    assert point["name"] == point["page_name"] == point["short_label"] == catalog["point"]["name"] == "قلعهٔ الموت"
    assert point["kind"] == point["importance"] == "primary"
    assert point["seo_indexable"] is True
    assert point["category_key"] == catalog["point"]["category_key"] == "fort"
    assert point["place_type"] == "landmark"
    assert "قلعه حسن صباح" in point["aliases"]
    assert point["source_urls"] and point["elevation_source"]
    assert point["seo"]["title"] == "آب‌وهوای قلعهٔ الموت؛ دما، باد و بارش | هواچ"
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (36.44478, 50.58621, 2080)
    assert catalog["routes"] == {}
    assert catalog["point"]["is_popular"] is False

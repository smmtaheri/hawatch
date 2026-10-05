import json
from pathlib import Path

from hawatch.modules.catalog.catalog import _validate_document_shape


def test_olang_is_a_searchable_point_only_forest_with_consistent_identity():
    directory = Path(__file__).parents[1] / "fixtures/catalog"
    document = json.loads((directory / "olang_forest_v1.json").read_text())
    _validate_document_shape(document)
    slug = document["primary_point"]
    assert slug == document["point"]["slug"] == "olang-forest"
    assert set(document["weather_points"]) == {slug}
    point = document["weather_points"][slug]
    assert point["name"] == point["page_name"] == document["point"]["name"] == "جنگل اولنگ"
    assert point["place_type"] == point["category_key"] == document["point"]["category_key"] == "forest"
    assert point["kind"] == point["importance"] == "primary"
    assert point["seo_indexable"] is document["point"]["seo_indexable"] is True
    assert document["point"]["is_active"] is True
    assert document["point"]["is_popular"] is False
    assert document["routes"] == {} and document["shared_weather_points"] == []
    for field in ("latitude", "longitude", "elevation_m", "climate"):
        assert point[field] == document["point"][field]
    assert point["elevation_m"] == 1704
    assert point["source_urls"] and point["elevation_source"]
    assert "مینودشت" in point["identity_summary"]
    owners = [p.name for p in directory.glob("*.json")
              if slug in json.loads(p.read_text()).get("weather_points", {})]
    assert owners == ["olang_forest_v1.json"]

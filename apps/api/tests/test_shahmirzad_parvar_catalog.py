import json
from pathlib import Path

from hawatch.modules.catalog.catalog import _validate_document_shape


def test_shahmirzad_cluster_has_distinct_searchable_point_only_destinations():
    directory = Path(__file__).parents[1] / "fixtures/catalog"
    document = json.loads((directory / "shahmirzad_parvar_v1.json").read_text())
    _validate_document_shape(document)
    points = document["weather_points"]
    assert set(points) == {
        "rudbarak-shahmirzad-forest", "rudbarak-shahmirzad",
        "parvar", "parvar-protected-area", "shahmirzad",
    }
    assert document["routes"] == {} and document["shared_weather_points"] == []
    assert document["point"]["is_popular"] is False
    for slug, point in points.items():
        assert point["name"] == point["page_name"]
        assert point["kind"] == point["importance"] == "primary"
        assert point["seo_indexable"] is True
        assert point["source_urls"] and point["elevation_source"]
        owners = [p.name for p in directory.glob("*.json")
                  if slug in json.loads(p.read_text()).get("weather_points", {})]
        assert owners == ["shahmirzad_parvar_v1.json"]
    assert points["shahmirzad"]["place_type"] == points["shahmirzad"]["category_key"] == "city"
    assert points["parvar"]["category_key"] == points["rudbarak-shahmirzad"]["category_key"] == "village"
    for prefix, village in [("rudbarak-shahmirzad-forest", "rudbarak-shahmirzad"),
                            ("parvar-protected-area", "parvar")]:
        assert points[prefix]["category_key"] == "forest"
        assert (points[prefix]["latitude"], points[prefix]["longitude"]) != (
            points[village]["latitude"], points[village]["longitude"])

import json
from pathlib import Path


def test_dalanper_is_an_indexable_point_only_peak():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/dalanper_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "dalanper"
    assert catalog["routes"] == {}
    point = catalog["weather_points"]["dalanper"]
    assert point["seo_indexable"] is True
    assert point["place_type"] == "summit"
    assert point["latitude"] == 37.1615
    assert point["longitude"] == 44.7899

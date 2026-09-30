import json
from pathlib import Path


def test_golestan_national_park_cluster_has_independent_point_only_destinations():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/golestan_national_park_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    expected = {
        "golestan-national-park",
        "tangrah-village",
        "aghsu-waterfall",
        "almeh-valley",
        "mirza-baylu-plain",
    }
    assert set(catalog["weather_points"]) == expected
    assert catalog["routes"] == {}
    assert catalog["primary_point"] == "golestan-national-park"

    for slug, point in catalog["weather_points"].items():
        assert point["kind"] == "primary"
        assert point["seo_indexable"] is True
        assert point["latitude"] and point["longitude"]
        assert point["elevation_m"] > 0
        assert "نقطهٔ نماینده" not in json.dumps(point, ensure_ascii=False)


import json
from pathlib import Path


def test_sangdeh_beech_forest_is_a_destination_and_keeps_its_route_anchor():
    catalog = json.loads(
        (Path(__file__).parents[1] / "fixtures/catalog/khornoro_v1.json").read_text()
    )
    slug = "sangdeh-beech-forest"
    point = catalog["weather_points"][slug]
    assert point["name"] == point["page_name"] == point["short_label"] == "جنگل راش سنگده"
    assert point["kind"] == point["importance"] == "primary"
    assert point["seo_indexable"] is True
    assert point["place_type"] == point["category_key"] == "forest"
    assert "جنگل مرسی‌سی" in point["aliases"]
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (36.01506, 53.22320, 1888)
    route = catalog["routes"]["sangdeh_to_khornoro"]
    assert route["points"][2] == slug
    assert route["timing"]["cumulative_minutes"][slug] == 300
    assert route["one_way_minutes"] == 690
    assert len(route["points"]) == 5
    assert catalog["weather_points"]["khornoro-sangdeh-village"]["seo_indexable"] is True
    assert catalog["weather_points"]["khornoro-varpi-village"]["seo_indexable"] is True

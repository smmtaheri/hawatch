import json
from pathlib import Path


def catalog():
    return json.loads((Path(__file__).parents[1] / "fixtures/catalog/abnik_waterfall_v1.json").read_text())


def test_abnik_waterfall_has_consistent_independent_identity():
    c = catalog()
    from hawatch.modules.catalog.catalog import _validate_document_shape
    _validate_document_shape(c)
    p = c["weather_points"]["abnik-waterfall"]
    assert c["primary_point"] == c["point"]["slug"] == "abnik-waterfall"
    assert p["name"] == p["page_name"] == p["short_label"] == "آبشار آبنیک"
    assert p["kind"] == p["importance"] == "primary" and p["seo_indexable"]
    assert p["place_type"] == p["category_key"] == "waterfall"
    assert (p["latitude"], p["longitude"], p["elevation_m"]) == (36.013218, 51.62116, 2740)
    assert "آبشار یخی آبنیک" in p["aliases"]
    assert c["point"]["is_popular"] is False


def test_village_reused_and_actual_junction_not_a_camp():
    c = catalog()
    assert c["shared_weather_points"] == ["khersang-abnik-village"]
    assert "khersang-abnik-village" not in c["weather_points"]
    r = c["routes"]["village"]
    assert r["points"] == ["khersang-abnik-village", "abnik-waterfall-junction", "abnik-waterfall"]
    j = c["weather_points"]["abnik-waterfall-junction"]
    assert j["seo_indexable"] is False and j["name_status"] == "descriptive"
    assert any("136184441" in url for url in j["source_urls"])
    assert (j["latitude"], j["longitude"], j["elevation_m"]) == (36.010866, 51.623547, 2678)
    times = [r["timing"]["cumulative_minutes"][slug] for slug in r["points"]]
    assert times == [0, 90, 120] and r["one_way_minutes"] == times[-1]
    assert r["distance_km"] == 3.73 and r["ascent_m"] == 360
    assert r["timing_status"] == "estimated" and r["timing"]["uncertainty_minutes"] == 30
    assert "یخ‌زدگی" in r["public_note"] and "یخ‌نوردی" in r["public_note"]
    assert not any("کمپ" in row["name"] for row in c["weather_points"].values())

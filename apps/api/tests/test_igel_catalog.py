import json
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "fixtures/catalog/igel_v1.json"


def catalog():
    return json.loads(CATALOG.read_text())


def test_igel_has_two_independent_destinations_and_one_real_support_landmark():
    c = catalog()
    p = c["weather_points"]
    assert c["primary_point"] == c["point"]["slug"] == "igel-waterfall"
    assert {slug for slug, row in p.items() if row["seo_indexable"]} == {"igel", "igel-waterfall"}
    for slug, name, category in [
        ("igel", "روستای ایگل", "village"),
        ("igel-waterfall", "آبشار ایگل", "waterfall"),
    ]:
        row = p[slug]
        assert row["name"] == row["page_name"] == row["short_label"] == name
        assert row["place_type"] == row["category_key"] == category
        assert row["kind"] == row["importance"] == "primary"
        assert row["source_urls"] and row["elevation_source"] and row["image"]
    junction = p["igel-waterfall-junction"]
    assert junction["name"] == "دوراهی مسیر آبشار ایگل"
    assert junction["kind"] == "route_point"
    assert junction["seo_indexable"] is False
    assert junction["name_status"] == "descriptive"


def test_igel_outbound_route_uses_no_camp_or_unverified_meadow():
    c = catalog()
    assert len(c["routes"]) == 1
    r = c["routes"]["village"]
    assert r["points"] == ["igel", "igel-waterfall-junction", "igel-waterfall"]
    assert r["slug"] == "igel-waterfall"
    assert r["origin"] == "روستای ایگل" and r["target_label"] == "آبشار ایگل"
    times = [r["timing"]["cumulative_minutes"][slug] for slug in r["points"]]
    assert times == [0, 75, 150]
    assert r["one_way_minutes"] == times[-1]
    assert r["timing_status"] == "estimated"
    assert r["timing"]["uncertainty_minutes"] == 45
    assert 3.2 < r["distance_km"] < 3.4  # outbound only; not the 6.65 km round-trip
    assert 350 <= r["ascent_m"] <= 420
    assert all(row["place_type"] != "meadow" for row in c["weather_points"].values())
    assert not any(word in row["name"] for row in c["weather_points"].values() for word in ["استراحت", "کمپ", "نانوایی", "سوپر"])


def test_igel_dem_coordinates_and_catalog_shape():
    c = catalog()
    for slug, coords in [
        ("igel", (35.909357, 51.490059, 1975)),
        ("igel-waterfall-junction", (35.905428, 51.470757, 2142)),
        ("igel-waterfall", (35.898319, 51.46923, 2351)),
    ]:
        p = c["weather_points"][slug]
        assert (p["latitude"], p["longitude"], p["elevation_m"]) == coords
    from hawatch.modules.catalog.catalog import _validate_document_shape

    _validate_document_shape(c)

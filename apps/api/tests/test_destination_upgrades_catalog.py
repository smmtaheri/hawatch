import json
from pathlib import Path

ROOT = Path(__file__).parents[1] / "fixtures/catalog"


def catalog(filename):
    return json.loads((ROOT / filename).read_text())


def test_upgraded_points_have_consistent_indexable_identities():
    for filename, slug, name, family in [
        ("khersang_v1.json", "dasht-janestoon", "دشت جانستون", "meadow"),
        ("rizan_v3.json", "afjeh", "روستای افجه", "village"),
        ("dobarar_v1.json", "hoir-lake", "دریاچهٔ هویر", "lake"),
    ]:
        point = catalog(filename)["weather_points"][slug]
        assert point["name"] == point["page_name"] == name
        assert point["kind"] == point["importance"] == "primary"
        assert point["seo_indexable"] is True
        assert point["place_type"] == point["category_key"] == family
        for field in ("tile_name", "short_label", "category", "region", "image", "source_urls"):
            assert point[field]


def test_janestoon_meadow_keeps_shared_route_timing_and_coordinates():
    owner = catalog("khersang_v1.json")
    point = owner["weather_points"]["dasht-janestoon"]
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (36.013638, 51.622561, 2773)
    assert owner["routes"]["abnik_to_khersang_middle"]["timing"]["cumulative_minutes"]["dasht-janestoon"] == 90
    consumer = catalog("janestoon_v1.json")
    assert "dasht-janestoon" in consumer["shared_weather_points"]
    assert "dasht-janestoon" not in consumer["weather_points"]
    for key in ("east", "west"):
        assert consumer["routes"][key]["timing"]["cumulative_minutes"]["dasht-janestoon"] == 70


def test_afjeh_upgrade_does_not_move_route_origins_or_merge_distant_access():
    c = catalog("rizan_v3.json")
    point = c["weather_points"]["afjeh"]
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (35.860912, 51.693294, 2072)
    for slug in ("afjeh-hoyej-rizan", "andar-person-rizan", "afjeh-hoyej-person"):
        assert c["routes"][slug]["points"][0] == "afjeh"
        assert c["routes"][slug]["origin"] == "روستای افجه"
    assert catalog("atash_kuh_v1.json")["weather_points"]["atash-kuh-afjeh-trailhead"]["seo_indexable"] is False


def test_hoir_lake_is_not_the_high_altitude_viewpoint():
    c = catalog("dobarar_v1.json")
    lake = c["weather_points"]["hoir-lake"]
    view = c["weather_points"]["dobrar-east-hoir-viewpoint"]
    assert (lake["latitude"], lake["longitude"], lake["elevation_m"]) == (35.7315, 52.2446, 2875)
    assert (view["latitude"], view["longitude"], view["elevation_m"]) == (35.756097, 52.236203, 3532)
    assert view["seo_indexable"] is False
    assert view["place_type"] != "lake"
    route = next(r for r in c["routes"].values() if r["slug"] == "tar-to-dobrar-east")
    assert route["points"] == ["tar-lake", "dobrar-east-hoir-viewpoint", "dobrar-east"]
    assert route["timing"]["cumulative_minutes"]["dobrar-east-hoir-viewpoint"] == 150
    assert route["one_way_minutes"] == 300
    assert route["distance_km"] == 6.2 and route["ascent_m"] == 1059
    assert "hoir-lake" not in route["points"]

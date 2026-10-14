import json
from pathlib import Path


CATALOG_DIR = Path(__file__).parents[1] / "fixtures" / "catalog"


def _catalog(filename):
    return json.loads((CATALOG_DIR / filename).read_text(encoding="utf-8"))


def test_darabad_independent_foot_destinations_are_short_and_searchable():
    catalog = _catalog("darabad_v1.json")
    points = catalog["weather_points"]

    assert "darabad-chalmags-waterfall" not in points
    for slug in ("chal-mags-darabad", "haft-hoz"):
        assert points[slug]["kind"] == "primary"
        assert points[slug]["importance"] == "primary"
        assert points[slug]["seo_indexable"] is True
    assert points["chal-mags-darabad"]["page_name"] == "آبشار چال‌مگس دارآباد"
    assert points["haft-hoz"]["page_name"] == "سر هفت‌حوض دارآباد"


def test_dorfak_village_pages_are_independent_but_route_waypoints_stay_noindex():
    catalog = _catalog("dorfak_v2.json")
    points = catalog["weather_points"]

    assert "dorfak-west-shirkuh" not in points
    assert "dorfak-south-estakhrgah" not in points
    for slug in ("shirkuh-gilan", "estakhrgah-gilan"):
        assert points[slug]["kind"] == "primary"
        assert points[slug]["importance"] == "primary"
        assert points[slug]["seo_indexable"] is True
    assert points["dorfak-east-tir-bargh"]["seo_indexable"] is False


def test_sabalan_uses_concise_point_slugs_without_indexing_technical_waypoints():
    catalog = _catalog("sabalan_v1.json")
    points = catalog["weather_points"]

    assert "sabalan-alvares-ski-resort" not in points
    assert "sabalan-shabil" not in points
    assert points["alvares-ski-resort"]["page_name"] == "پیست اسکی آلوارس"
    assert points["alvares-ski-resort"]["seo_indexable"] is True
    assert points["sabalan-west-trailhead"]["seo_indexable"] is False
    assert points["sabalan"]["page_name"] == "قلهٔ سبلان"


def test_peak_catalog_route_point_references_and_timing_keys_stay_in_sync():
    for filename in ("darabad_v1.json", "dorfak_v2.json", "sabalan_v1.json"):
        catalog = _catalog(filename)
        point_slugs = set(catalog["weather_points"])
        for route in catalog["routes"].values():
            assert set(route["points"]) <= point_slugs
            assert set(route["timing"]["cumulative_minutes"]) == set(route["points"])

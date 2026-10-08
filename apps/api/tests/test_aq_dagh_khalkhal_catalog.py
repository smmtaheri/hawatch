import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOG = json.loads(
    (Path(__file__).parents[1] / "fixtures/catalog/aq_dagh_khalkhal_v1.json").read_text()
)


def test_aq_dagh_identity_and_catalog_contract():
    assert not validate_catalog_document(CATALOG)
    assert CATALOG["primary_point"] == "aq-dagh-khalkhal"
    points = CATALOG["weather_points"]
    assert set(points) == {"aq-dagh-khalkhal", "merajin", "bafrajerd"}
    for point in points.values():
        assert point["name"] == point["page_name"] == point["short_label"]
        assert point["kind"] == point["importance"] == "primary"
        assert point["seo_indexable"]
        assert point["routes"] == {}
        assert point["source_urls"]
        assert "DEM" in point["elevation_source"]
        assert len(point["elevation_source"]) <= 255


def test_aq_dagh_keeps_unverified_springs_and_routes_unpublished():
    # Neither downloaded track locates the named springs reliably. A valid
    # summit must remain publishable without fabricated intermediate points.
    assert CATALOG["routes"] == {}
    assert CATALOG["weather_points"]["aq-dagh-khalkhal"]["place_type"] == "summit"
    assert CATALOG["point"]["category_key"] == "mountain"
    assert not CATALOG["point"]["is_popular"]


def test_aq_dagh_villages_are_not_distant_track_start_coordinates():
    points = CATALOG["weather_points"]
    assert points["merajin"]["latitude"] == 37.39072
    assert points["merajin"]["longitude"] == 48.508408
    assert points["bafrajerd"]["latitude"] == 37.49444
    assert points["bafrajerd"]["longitude"] == 48.55528
    assert all(points[s]["place_type"] == "village" for s in ("merajin", "bafrajerd"))

import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "fixtures/catalog/ruteh_peak_v1.json"


def test_ruteh_is_distinct_indexable_summit_without_technical_public_routes():
    catalog = json.loads(CATALOG.read_text())
    assert catalog["primary_point"] == catalog["point"]["slug"] == "ruteh-peak"
    assert catalog["routes"] == {}
    assert catalog["shared_weather_points"] == []
    assert set(catalog["weather_points"]) == {"ruteh-peak"}
    point = catalog["weather_points"]["ruteh-peak"]
    assert point["name"] == point["page_name"] == point["short_label"] == "قلهٔ روته"
    assert point["place_type"] == "summit"
    assert point["category_key"] == catalog["point"]["category_key"] == "mountain"
    assert point["kind"] == point["importance"] == "primary"
    assert point["seo_indexable"] and catalog["point"]["seo_indexable"]
    assert not catalog["point"]["is_popular"]
    assert "روستای هم‌نام" in point["identity_summary"]
    assert "Route عمومی ثبت نشده" in point["identity_summary"]
    assert len(point["source_urls"]) == 2


def test_ruteh_forecast_uses_verified_dem_and_consistent_profile():
    catalog = json.loads(CATALOG.read_text())
    point = catalog["weather_points"]["ruteh-peak"]
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (35.9842709, 51.5474788, 3118)
    assert point["status"] == "provisional"
    assert "GLO-90 DEM" in point["elevation_source"]
    for field in ("name", "latitude", "longitude", "elevation_m", "climate", "category_key"):
        assert catalog["point"][field] == point[field]
    for field, limit in {"name": 80, "page_name": 160, "short_label": 80, "region": 64,
                         "identity_summary": 255, "elevation_source": 255}.items():
        assert len(point[field]) <= limit
    assert len(catalog["catalog_version"]) <= 32

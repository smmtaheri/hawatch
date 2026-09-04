from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError

from hawatch.modules.catalog.tochal import seed_tochal_catalog
from hawatch.modules.catalog.catalog import seed_catalog
from hawatch.modules.catalog.validation import validate_catalog_document
from hawatch.modules.catalog.validation import validate_database_catalog
from hawatch.modules.forecasts.models import WeatherPoint


def _catalog_paths() -> list[Path]:
    return sorted(Path(__file__).parents[1].joinpath("fixtures/catalog").glob("*.json"))


def test_checked_in_catalogs_have_valid_identity_and_route_contracts():
    assert _catalog_paths()
    for path in _catalog_paths():
        issues = validate_catalog_document(json.loads(path.read_text(encoding="utf-8")))
        assert not [issue for issue in issues if issue.level == "error"], path.name


def test_independent_point_slug_must_be_lowercase_hyphenated():
    catalog = {
        "catalog_version": "test-v1",
        "point": {"slug": "test-summit"},
        "primary_point": "test-summit",
        "weather_points": {
            "test_summit": {
                "kind": "primary",
                "name": "قلهٔ تست",
                "page_name": "قلهٔ تست",
                "short_label": "تست",
                "place_type": "summit",
                "identity_summary": "مقصد تست",
                "importance": "primary",
                "name_status": "official",
                "source_urls": ["https://example.com"],
                "latitude": 35.0,
                "longitude": 52.0,
                "elevation_m": 2000,
            },
            "test_point_name": {
                "name": "نقطهٔ تست",
                "page_name": "نقطهٔ تست",
                "short_label": "تست",
                "place_type": "landmark",
                "identity_summary": "نقطهٔ تست",
                "importance": "support",
                "name_status": "descriptive",
                "source_urls": ["https://example.com"],
                "latitude": 35.1,
                "longitude": 52.1,
                "elevation_m": 2100,
            },
        },
        "routes": {},
    }

    assert any(issue.code == "point-slug" for issue in validate_catalog_document(catalog))


def test_route_requires_origin_landmark_and_target():
    catalog = {
        "catalog_version": "test-v1",
        "point": {"slug": "test-summit"},
        "primary_point": "test-summit",
        "weather_points": {
            "test-summit": {
                "kind": "primary",
                "name": "قلهٔ تست",
                "page_name": "قلهٔ تست",
                "short_label": "تست",
                "place_type": "summit",
                "identity_summary": "مقصد تست",
                "importance": "primary",
                "name_status": "official",
                "source_urls": ["https://example.com"],
                "latitude": 35.0,
                "longitude": 52.0,
                "elevation_m": 2000,
            },
            "test-start": {
                "name": "مبدأ تست",
                "page_name": "مبدأ تست",
                "short_label": "مبدأ",
                "place_type": "trailhead",
                "identity_summary": "مبدأ تست",
                "importance": "support",
                "name_status": "official",
                "source_urls": ["https://example.com"],
                "latitude": 35.1,
                "longitude": 52.1,
                "elevation_m": 1500,
            },
        },
        "routes": {
            "test-route": {"slug": "test-route", "sort_order": 1, "points": ["test-start", "test-summit"]}
        },
    }

    assert any(issue.code == "route-chain" for issue in validate_catalog_document(catalog))


def test_catalog_rejects_an_unsupported_demo_climate_before_import():
    path = Path(__file__).parents[1] / "fixtures/catalog/eskelim_v1.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["weather_points"]["eskelim-parking"]["climate"] = "forest"

    issues = validate_catalog_document(catalog)

    assert any(issue.code == "climate-profile" and issue.level == "error" for issue in issues)


def test_weather_point_model_validation_rejects_an_unsupported_demo_climate():
    point = WeatherPoint(
        slug="test-forest-point",
        name="نقطهٔ تست جنگلی",
        location=Point(52.0, 35.0, srid=4326),
        climate="forest",
    )

    with pytest.raises(ValidationError, match="Unsupported demo climate profile"):
        point.full_clean(validate_unique=False)


@pytest.mark.django_db
def test_seed_catalog_rejects_an_unsupported_demo_climate_without_writing_rows():
    path = Path(__file__).parents[1] / "fixtures/catalog/eskelim_v1.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["weather_points"]["eskelim-parking"]["climate"] = "forest"

    with pytest.raises(ValueError, match="climate-profile"):
        seed_catalog(catalog=catalog)

    assert WeatherPoint.objects.count() == 0


@pytest.mark.django_db
def test_seeded_catalog_passes_database_identity_validation():
    seed_tochal_catalog()

    issues = validate_database_catalog(strict=True)

    assert not [issue for issue in issues if issue.level == "error"], issues
    assert not [issue for issue in issues if issue.level == "warning"], issues

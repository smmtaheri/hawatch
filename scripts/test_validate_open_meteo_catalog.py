from __future__ import annotations

import json

from . import validate_open_meteo_catalog as validator


def _catalog(tmp_path):
    catalog = {
        "catalog_version": "hawatch-test-v1",
        "destination_weather_point": "test_summit",
        "destination": {
            "slug": "test-mountain",
            "tile_name": "آزمایشی",
            "name": "قلهٔ آزمایشی",
            "short_category": "کوه",
            "category": "قله و مسیرهای کوهستانی",
            "category_key": "mountain",
            "region": "آزمایشی",
            "elevation_m": 1000,
            "latitude": 35.0,
            "longitude": 51.0,
            "image": "/images/fallback.png",
            "image_alt": "قلهٔ آزمایشی",
            "climate": "alpine",
        },
        "weather_points": {
            "test_summit": {
                "name": "قلهٔ آزمایشی",
                "latitude": 35.0,
                "longitude": 51.0,
                "elevation_m": 1000,
                "status": "provisional",
                "elevation_source": "test",
            }
        },
        "routes": {"main": {"slug": "test-main", "points": ["test_summit"]}},
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    return path


def _forecast_rows(points, *, distance=0.1, elevation=1000, missing=None, hour_count=2):
    return [
        {
            **point,
            "provider_latitude": point["latitude"],
            "provider_longitude": point["longitude"],
            "provider_elevation_m": elevation,
            "provider_distance_km": distance,
            "hour_count": hour_count,
            "missing_hourly_fields": list(missing or []),
            "hourly_length_mismatches": [],
        }
        for point in points
    ]


def test_catalog_dem_mismatch_is_blocking(tmp_path, monkeypatch):
    path = _catalog(tmp_path)
    monkeypatch.setattr(
        validator,
        "_query_elevation",
        lambda points, *, endpoint, timeout: [{**point, "dem_elevation_m": 1201} for point in points],
    )
    monkeypatch.setattr(
        validator,
        "_query_forecast",
        lambda points, *, endpoint, forecast_days, timeout: _forecast_rows(points),
    )

    report = validator.validate_catalog(path)

    assert report["summary"]["pass"] is False
    assert any("catalog/DEM elevation delta" in item for item in report["errors"])
    assert not report["warnings"]


def test_provider_distance_and_hourly_shape_are_blocking(tmp_path, monkeypatch):
    path = _catalog(tmp_path)
    monkeypatch.setattr(
        validator,
        "_query_elevation",
        lambda points, *, endpoint, timeout: [{**point, "dem_elevation_m": 1000} for point in points],
    )
    monkeypatch.setattr(
        validator,
        "_query_forecast",
        lambda points, *, endpoint, forecast_days, timeout: _forecast_rows(
            points,
            distance=5.1,
            elevation=None,
            missing=("temperature_2m", "precipitation"),
            hour_count=0,
        ),
    )

    report = validator.validate_catalog(path)

    assert report["summary"]["pass"] is False
    assert any("grid resolution distance" in item for item in report["errors"])
    assert any("missing temperature_2m, precipitation" in item for item in report["errors"])
    assert any("no elevation metadata" in item for item in report["errors"])

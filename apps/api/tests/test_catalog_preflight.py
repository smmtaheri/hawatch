from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from hawatch.modules.catalog.catalog import load_catalog_file
from hawatch.modules.catalog.preflight import run_catalog_preflight
from hawatch.modules.catalog.tochal import seed_tochal_catalog
from hawatch.modules.routes.models import Route


@pytest.mark.django_db
def test_catalog_preflight_reports_pending_provider_data_without_mutating_catalog():
    seed_tochal_catalog()

    report = run_catalog_preflight(destination_slug="tochal")

    assert report["summary"]["destination_count"] == 1
    assert report["summary"]["route_count"] == 5
    assert report["summary"]["ingestible_point_count"] > 0
    assert report["summary"]["error_count"] == 0
    assert report["summary"]["warning_count"] > 0
    assert any("no successful Open-Meteo resolution" in item for item in report["warnings"])


@pytest.mark.django_db
def test_catalog_preflight_requires_provider_data_after_ingest():
    seed_tochal_catalog()

    report = run_catalog_preflight(destination_slug="tochal", require_forecast=True)

    assert report["summary"]["pass"] is False
    assert report["summary"]["error_count"] > 0
    assert any("no successful Open-Meteo resolution" in item for item in report["errors"])


@pytest.mark.django_db
def test_catalog_preflight_detects_incomplete_active_route():
    seed_tochal_catalog()
    route = Route.objects.get(slug="tochal-darband")
    route.one_way_minutes = None
    route.timing_status = Route.TimingStatus.PENDING
    route.save(update_fields=["one_way_minutes", "timing_status"])

    report = run_catalog_preflight(destination_slug="tochal")

    assert any("tochal-darband" in item and "timing is pending" in item for item in report["warnings"])


@pytest.mark.django_db
def test_catalog_preflight_accepts_destination_without_active_routes():
    seed_tochal_catalog()
    Route.objects.filter(destination__slug="tochal").update(is_active=False)

    report = run_catalog_preflight(destination_slug="tochal")

    assert report["summary"]["destination_count"] == 1
    assert report["summary"]["route_count"] == 0
    assert not any("no active live routes" in item for item in report["warnings"])


@pytest.mark.django_db
def test_seed_catalog_reads_stdin_and_check_only_does_not_write(capsys, monkeypatch):
    catalog = load_catalog_file()
    before = Route.objects.count()

    monkeypatch.setattr("sys.stdin", StringIO(json.dumps(catalog)))
    call_command("seed_catalog", "--stdin", "--check-only")

    assert Route.objects.count() == before
    assert "No database changes made" in capsys.readouterr().out


@pytest.mark.django_db
def test_seed_catalog_strict_conflict_fails_without_partial_import(monkeypatch):
    catalog = load_catalog_file()
    catalog["destination"]["slug"] = "strict-conflict"
    catalog["weather_points"]["strict-conflict-point"] = {
        "name": "تداخل دستی",
        "latitude": 35.8,
        "longitude": 51.4,
        "elevation_m": 1000,
    }
    catalog["destination_weather_point"] = "strict-conflict-point"
    from hawatch.modules.forecasts.models import WeatherPoint
    from django.contrib.gis.geos import Point
    from hawatch.modules.destinations.models import Destination

    destination = Destination.objects.create(
        slug="strict-conflict",
        tile_name="تداخل",
        name="تداخل",
        short_category="کوه",
        category="کوه",
        category_key="mountain",
        region="تهران",
        elevation_m=1000,
        location=Point(51.4, 35.8, srid=4326),
        image="/images/fallback.png",
        image_alt="تداخل",
        popular_order=999,
        climate="alpine",
    )
    WeatherPoint.objects.create(
        slug="strict-conflict-point",
        name="نقطهٔ دستی",
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.4, 35.8, srid=4326),
        elevation_m=1000,
        destination=destination,
        data_mode="live",
        fixture_managed=False,
    )

    with pytest.raises(CommandError):
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(catalog)))
        call_command(
            "seed_catalog",
            "--stdin",
            "--strict",
        )

    assert not Route.objects.filter(destination=destination).exists()

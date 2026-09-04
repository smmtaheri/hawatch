from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.db.models import Q

from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route
from hawatch.modules.catalog.tochal import seed_tochal_catalog


def _point(slug: str, *, fixture_managed: bool) -> WeatherPoint:
    return WeatherPoint.objects.create(
        slug=slug,
        name=slug,
        page_name=slug,
        short_label=slug,
        place_type="landmark",
        identity_summary=slug,
        importance="support",
        name_status="descriptive",
        source_urls=["https://example.test/point"],
        kind=WeatherPoint.Kind.SHARED,
        location=Point(52.0, 35.0, srid=4326),
        elevation_m=2000,
        climate="alpine",
        data_mode="live",
        is_active=True,
        ingest_enabled=True,
        fixture_managed=fixture_managed,
    )


@pytest.mark.django_db
def test_catalog_sync_upgrades_existing_database_and_is_idempotent():
    seed_tochal_catalog()
    stale = _point("legacy-fixture-point", fixture_managed=True)
    manual = _point("operator-point", fixture_managed=False)
    stale_route = Route.objects.create(
        slug="legacy-fixture-route",
        title="مسیر قدیمی",
        subtitle="قدیمی",
        trail_label="قدیمی",
        origin="مبدأ",
        target_label="نقطه",
        region="استان",
        origin_location=Point(52.0, 35.0, srid=4326),
        data_mode="live",
        fixture_managed=True,
    )
    before_counts = (WeatherPoint.objects.count(), Route.objects.count())
    dry_run_output = StringIO()

    call_command("sync_catalog", "--dry-run", stdout=dry_run_output)

    assert (WeatherPoint.objects.count(), Route.objects.count()) == before_counts
    assert "would deactivate point legacy-fixture-point" in dry_run_output.getvalue()
    assert "would deactivate route legacy-fixture-route" in dry_run_output.getvalue()

    call_command("sync_catalog", "--apply", stdout=StringIO())

    assert WeatherPoint.objects.filter(is_active=True, fixture_managed=True).exclude(Q(slug__startswith="dest:") | Q(slug__startswith="route:")).count() == 127
    assert Route.objects.filter(is_active=True).count() == 35
    assert not WeatherPoint.objects.get(pk=stale.pk).is_active
    assert not Route.objects.get(pk=stale_route.pk).is_active
    assert WeatherPoint.objects.get(pk=manual.pk).is_active

    point_updated_at = WeatherPoint.objects.get(slug="tochal").updated_at
    route_updated_at = Route.objects.get(slug="tochal-darband").updated_at
    second_output = StringIO()
    call_command("sync_catalog", "--apply", stdout=second_output)

    assert "created=0, updated=0" in second_output.getvalue()
    assert WeatherPoint.objects.get(slug="tochal").updated_at == point_updated_at
    assert Route.objects.get(slug="tochal-darband").updated_at == route_updated_at

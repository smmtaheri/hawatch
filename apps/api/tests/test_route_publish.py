"""Admin/DB publish path produces valid route timeline without fixture import."""

from __future__ import annotations

from django.contrib.gis.geos import Point

import pytest
from rest_framework.test import APIClient

from hawatch.modules.catalog.tochal import seed_tochal_catalog
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint
from hawatch.modules.routes.publish import normalize_and_publish_route
from hawatch.modules.routes.timing import route_timing_complete


@pytest.mark.django_db
def test_admin_style_route_publish_without_fixture_import():
    seed_tochal_catalog()
    destination = Destination.objects.get(slug="tochal")
    start = WeatherPoint.objects.create(
        slug="admin_start",
        name="شروع ادمین",
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.42, 35.83, srid=4326),
        elevation_m=1800,
        destination=destination,
        data_mode="live",
        is_active=True,
        ingest_enabled=True,
        fixture_managed=False,
        status=WeatherPoint.Status.PROVISIONAL,
    )
    mid = WeatherPoint.objects.create(
        slug="admin_mid",
        name="میانه ادمین",
        kind=WeatherPoint.Kind.SHARED,
        location=Point(51.425, 35.85, srid=4326),
        elevation_m=2500,
        destination=destination,
        data_mode="live",
        is_active=True,
        ingest_enabled=True,
        fixture_managed=False,
        status=WeatherPoint.Status.PROVISIONAL,
    )
    summit = WeatherPoint.objects.get(slug="tochal_summit")

    route = Route.objects.create(
        slug="tochal-admin-publish",
        destination=destination,
        title="مسیر ادمین",
        subtitle="بدون fixture",
        trail_label="ادمین",
        origin="شروع",
        destination_label="قله",
        region="تهران",
        distance_km=8.0,
        ascent_m=2100,
        one_way_minutes=180,
        timing_status=Route.TimingStatus.ESTIMATED,
        timing_method="admin-publish-v1",
        timing_version="admin-v1",
        timing_confidence="low",
        timing_uncertainty_minutes=40,
        timing_source_urls=["https://example.test/admin"],
        origin_location=start.location,
        data_mode="live",
        is_active=True,
        fixture_managed=False,
    )
    # Intentionally messy order and stale denormalized fields.
    RoutePoint.objects.create(
        route=route,
        slug="admin_mid",
        weather_point=mid,
        name="stale",
        elevation_m=1,
        location=Point(51.0, 35.0, srid=4326),
        cumulative_minutes=90,
        segment_minutes=None,
        timing_status=RoutePoint.TimingStatus.ESTIMATED,
        sort_order=40,
        data_mode="live",
        fixture_managed=False,
    )
    RoutePoint.objects.create(
        route=route,
        slug="admin_start",
        weather_point=start,
        name="stale-start",
        elevation_m=1,
        location=Point(51.0, 35.0, srid=4326),
        cumulative_minutes=0,
        segment_minutes=None,
        timing_status=RoutePoint.TimingStatus.ESTIMATED,
        sort_order=10,
        data_mode="live",
        fixture_managed=False,
    )
    RoutePoint.objects.create(
        route=route,
        slug="tochal_summit",
        weather_point=summit,
        name="stale-summit",
        elevation_m=1,
        location=Point(51.0, 35.0, srid=4326),
        cumulative_minutes=180,
        segment_minutes=None,
        timing_status=RoutePoint.TimingStatus.ESTIMATED,
        sort_order=99,
        data_mode="live",
        fixture_managed=False,
    )

    normalize_and_publish_route(route)

    route.refresh_from_db()
    points = list(route.points.order_by("sort_order"))
    assert [point.slug for point in points] == ["admin_start", "admin_mid", "tochal_summit"]
    assert [point.sort_order for point in points] == [1, 2, 3]
    assert [point.segment_minutes for point in points] == [0, 90, 90]
    assert points[0].name == "شروع ادمین"
    assert points[0].elevation_m == 1800
    assert route.origin_weather_point_id == start.id
    assert route.target_weather_point_id == summit.id
    assert route.timing_status == Route.TimingStatus.ESTIMATED
    assert route_timing_complete(
        timing_status=route.timing_status,
        one_way_minutes=route.one_way_minutes,
        points=points,
    )

    client = APIClient()
    body = client.get(
        "/api/v1/routes/tochal-admin-publish/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    assert body["timing_pending"] is False
    assert [point["slug"] for point in body["points"]] == ["admin_start", "admin_mid", "tochal_summit"]
    assert body["points"][0]["arrival_minutes"] == 360
    assert body["points"][-1]["arrival_minutes"] == 360 + 180


@pytest.mark.django_db
def test_incomplete_admin_route_demoted_to_pending():
    seed_tochal_catalog()
    destination = Destination.objects.get(slug="tochal")
    start = WeatherPoint.objects.get(slug="tochal-sarband-square")
    summit = WeatherPoint.objects.get(slug="tochal_summit")
    route = Route.objects.create(
        slug="tochal-admin-incomplete",
        destination=destination,
        title="ناقص",
        subtitle="",
        trail_label="",
        origin="a",
        destination_label="b",
        region="تهران",
        one_way_minutes=100,
        timing_status=Route.TimingStatus.ESTIMATED,
        timing_method="x",
        timing_version="y",
        timing_confidence="low",
        timing_uncertainty_minutes=10,
        timing_source_urls=["https://example.test"],
        origin_location=start.location,
        data_mode="live",
        is_active=True,
        fixture_managed=False,
    )
    RoutePoint.objects.create(
        route=route,
        slug="tochal-sarband-square",
        weather_point=start,
        name=start.name,
        elevation_m=start.elevation_m,
        location=start.location,
        cumulative_minutes=0,
        timing_status=RoutePoint.TimingStatus.ESTIMATED,
        sort_order=1,
        data_mode="live",
    )
    RoutePoint.objects.create(
        route=route,
        slug="tochal_summit",
        weather_point=summit,
        name=summit.name,
        elevation_m=summit.elevation_m,
        location=summit.location,
        cumulative_minutes=50,  # != one_way
        timing_status=RoutePoint.TimingStatus.ESTIMATED,
        sort_order=2,
        data_mode="live",
    )
    normalize_and_publish_route(route)
    route.refresh_from_db()
    assert route.timing_status == Route.TimingStatus.PENDING

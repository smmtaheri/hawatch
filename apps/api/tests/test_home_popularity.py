import json
import re
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.contrib.gis.geos import Point
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from hawatch.modules.analytics.models import PageViewEvent
from hawatch.modules.catalog.home import HOME_CATALOG_CACHE_KEY, home_catalog_data
from hawatch.modules.forecasts.models import ForecastSnapshot, WeatherPoint


@pytest.fixture(autouse=True)
def clear_home_catalog_cache():
    cache.delete(HOME_CATALOG_CACHE_KEY)
    yield
    cache.delete(HOME_CATALOG_CACHE_KEY)


@pytest.fixture
def catalog(db):
    slugs = ("tochal", "damavand", "alamkuh", "tar-lake")
    for order, slug in enumerate(slugs, start=1):
        WeatherPoint.objects.create(
            slug=slug,
            name=slug,
            page_name=slug,
            tile_name=slug,
            place_type="summit" if slug != "tar-lake" else "lake",
            kind=WeatherPoint.Kind.PRIMARY,
            importance="primary",
            seo_indexable=True,
            is_popular=True,
            popular_order=order,
            location=Point(51 + order / 10, 35 + order / 10, srid=4326),
            elevation_m=3000,
            data_mode="live",
        )
    WeatherPoint.objects.create(
        slug="technical-trail-stop",
        name="نقطهٔ فنی مسیر",
        kind=WeatherPoint.Kind.SHARED,
        importance="support",
        seo_indexable=False,
        place_type="trailhead",
        location=Point(52, 36, srid=4326),
        data_mode="live",
    )
    return set(slugs)


def record_visit(*, page_type, slug, visitor, navigation, days_ago=1):
    PageViewEvent.objects.create(
        page_type=page_type,
        page_slug=slug,
        visitor_hash=f"{visitor:064d}",
        navigation_id=f"nav-{navigation}",
        occurred_at=timezone.now() - timedelta(days=days_ago),
    )


@pytest.mark.django_db
@override_settings(DEMO_DATA_ENABLED=False)
def test_home_popularity_counts_unique_recent_destination_visitors_only(api_client, catalog):
    assert {"tochal", "damavand", "alamkuh", "tar-lake"} <= catalog
    # Three visitors for Damavand, with one visitor opening it twice.
    for visitor in range(3):
        record_visit(page_type="point", slug="damavand", visitor=visitor, navigation=visitor)
    record_visit(page_type="point", slug="damavand", visitor=0, navigation=10)
    for visitor in range(10, 12):
        record_visit(page_type="point", slug="tochal", visitor=visitor, navigation=visitor)
    record_visit(page_type="point", slug="alamkuh", visitor=20, navigation=20)

    # Route traffic and technical waypoints must not affect destination rank.
    for visitor in range(30, 38):
        record_visit(page_type="route", slug="tochal-darband", visitor=visitor, navigation=visitor)
    support = WeatherPoint.objects.filter(is_active=True).exclude(slug__in=catalog).first()
    if support:
        for visitor in range(40, 48):
            record_visit(page_type="point", slug=support.slug, visitor=visitor, navigation=visitor)
    record_visit(page_type="point", slug="tar-lake", visitor=50, navigation=50, days_ago=8)

    expected = ["damavand", "tochal", "alamkuh"]
    payload = home_catalog_data()
    assert [point["slug"] for point in payload["popular_points"][:3]] == expected

    response = api_client.get("/api/v1/points/")
    assert response.status_code == 200
    assert [point["slug"] for point in response.json()["results"][:3]] == expected
    assert response["Cache-Control"] == "public, max-age=60, s-maxage=300, stale-while-revalidate=60"


@pytest.mark.django_db
@override_settings(DEMO_DATA_ENABLED=False)
def test_home_api_reads_snapshot_metadata_without_loading_raw_provider_payload(api_client, catalog):
    generated_at = timezone.now()
    ForecastSnapshot.objects.create(
        provider="open-meteo",
        source="open-meteo-forecast",
        catalog_version="open-meteo-live",
        requested_at=generated_at,
        generated_at=generated_at,
        valid_from=generated_at,
        valid_to=generated_at + timedelta(days=7),
        status=ForecastSnapshot.Status.SUCCESS,
        freshness=ForecastSnapshot.Freshness.READY,
        raw_response={"batch_results": [{"provider_payload": "large"}]},
    )

    with CaptureQueriesContext(connection) as captured:
        response = api_client.get("/api/v1/points/")
        cached_response = api_client.get("/api/v1/points/")

    assert response.status_code == 200
    assert cached_response.status_code == 200
    meta = response.json()["meta"]
    assert meta["data_mode"] == "live"
    assert meta["provider"] == "open-meteo"
    assert meta["source"] == "open-meteo-forecast"
    assert meta["seed_version"] == "open-meteo-live"
    assert meta["freshness"] == "ready"
    assert meta["last_generated_time"] == meta["generated_at"]
    assert meta["forecast_validity"]["valid_from"]
    assert meta["forecast_validity"]["valid_to"]
    assert len(response.json()["results"]) == 4

    snapshot_table = ForecastSnapshot._meta.db_table.lower()
    snapshot_queries = [
        query["sql"]
        for query in captured.captured_queries
        if snapshot_table in query["sql"].lower()
    ]
    assert len(snapshot_queries) == 3  # Cold: home + API metadata; cache hit: API metadata.
    assert all("raw_response" not in query.lower() for query in snapshot_queries)


@pytest.mark.django_db
def test_home_html_embeds_the_ranked_first_paint_data(client, catalog):
    record_visit(page_type="point", slug="damavand", visitor=0, navigation=0)
    record_visit(page_type="point", slug="damavand", visitor=2, navigation=2)
    record_visit(page_type="point", slug="tochal", visitor=1, navigation=1)

    response = client.get("/")
    body = response.content.decode()
    match = re.search(
        r'<script id="home-initial-data" type="application/json">(.*?)</script>',
        body,
        re.DOTALL,
    )
    assert match
    data = json.loads(match.group(1))
    assert [point["slug"] for point in data["popular_points"][:2]] == ["damavand", "tochal"]
    assert data["catalog_counts"]["points"] > 0
    assert isinstance(data["catalog_counts"]["routes"], int)

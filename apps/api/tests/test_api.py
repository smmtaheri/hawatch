from datetime import datetime, timezone as dt_timezone
from xml.etree import ElementTree

import pytest
from django.db import connection
from django.db.models import Q
from rest_framework.test import APIClient

from hawatch.common.time import day_window, now_tehran
from hawatch.integrations.weather.demo import generate_reading
from hawatch.modules.catalog.seed import seed_demo_data
from hawatch.modules.catalog.sync import load_packaged_catalogs
from hawatch.modules.catalog.runtime import DESTINATIONS_PAGE_SIZE, publicly_visible_destinations
from hawatch.modules.forecasts.models import ForecastRecord, ForecastSnapshot, WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seeded(db):
    return seed_demo_data(force=True)


def _sitemap_lastmod(response, url):
    root = ElementTree.fromstring(response.content)
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    for node in root.findall(f"{namespace}url"):
        loc = node.find(f"{namespace}loc")
        if loc is not None and loc.text == url:
            value = node.find(f"{namespace}lastmod")
            return datetime.fromisoformat(value.text.replace("Z", "+00:00")) if value is not None else None
    return None


def _persist_live_forecast_record(point, generated_at):
    snapshot = ForecastSnapshot.objects.create(
        provider="open-meteo",
        requested_at=generated_at,
        generated_at=generated_at,
        status=ForecastSnapshot.Status.SUCCESS,
        freshness=ForecastSnapshot.Freshness.READY,
    )
    record = ForecastRecord.objects.filter(weather_point=point).first()
    assert record is not None
    record.pk = None
    record.snapshot = snapshot
    record.generated_at = generated_at
    record.data_mode = "live"
    record.provider = "open-meteo"
    record.source = "open-meteo-forecast"
    record.seed_version = "open-meteo-live"
    record.freshness = ForecastRecord.Freshness.READY
    record.save()
    return snapshot


def test_live_health(api_client):
    response = api_client.get("/api/v1/health/live/")
    assert response.status_code == 200
    assert response.json()["status"] == "live"


@pytest.mark.django_db
def test_ready_health_postgis(api_client, seeded):
    response = api_client.get("/api/v1/health/ready/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["postgis"] is True
    with connection.cursor() as cursor:
        cursor.execute("SELECT PostGIS_Version()")
        assert cursor.fetchone()[0]


@pytest.mark.django_db
def test_known_points_and_routes_exist(seeded):
    desired = load_packaged_catalogs()
    slugs = set(WeatherPoint.objects.filter(kind=WeatherPoint.Kind.PRIMARY).values_list("slug", flat=True))
    expected_primary = {
        str(data.get("primary_point") or data["point"].get("slug"))
        for _relative, data in desired.files
    }
    assert slugs == expected_primary
    route_slugs = set(Route.objects.values_list("slug", flat=True))
    assert route_slugs == set(desired.route_slugs)
    assert "tochal-darband" in route_slugs
    assert {"gahar-dorud", "gahar-aligudarz"} <= route_slugs
    assert Route.objects.filter(target_weather_point__slug="tochal").count() == 5
    assert RoutePoint.objects.filter(route__slug="tochal-darband").count() == 6


@pytest.mark.django_db
def test_all_active_catalog_points_honor_catalog_indexability(seeded):
    public_points = WeatherPoint.objects.filter(is_active=True).exclude(Q(slug__startswith="dest:") | Q(slug__startswith="route:"))
    desired = load_packaged_catalogs()

    assert set(public_points.values_list("slug", flat=True)) == set(desired.point_slugs)
    expected_indexable = {
        slug for slug, row in desired.point_rows.items() if row.get("seo_indexable", True)
    }
    assert set(public_points.filter(seo_indexable=True).values_list("slug", flat=True)) == expected_indexable
    assert public_points.filter(seo_indexable=False).exists()


@pytest.mark.django_db
def test_sitemap_contains_home_all_public_points_and_active_routes(api_client, seeded):
    response = api_client.get("/api/v1/seo/sitemap.xml")

    assert response.status_code == 200
    assert response["Cache-Control"] == "public, no-cache, must-revalidate"
    root = ElementTree.fromstring(response.content)
    locations = [node.text for node in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    desired = load_packaged_catalogs()
    expected_points = {
        f"https://hawatch.ir/points/{slug}"
        for slug in WeatherPoint.objects.filter(is_active=True, seo_indexable=True)
        .exclude(Q(slug__startswith="dest:") | Q(slug__startswith="route:"))
        .values_list("slug", flat=True)
    }
    expected_routes = {f"https://hawatch.ir/routes/{slug}" for slug in desired.route_slugs}
    expected_locations = {"https://hawatch.ir/", "https://hawatch.ir/destinations"} | expected_points | expected_routes
    assert set(locations) == expected_locations
    assert len(locations) == 2 + len(expected_points) + len(expected_routes)
    assert len(locations) == len(set(locations))
    assert locations[0] == "https://hawatch.ir/"
    assert locations[1] == "https://hawatch.ir/destinations"
    assert all(url.startswith("https://hawatch.ir/") and "?" not in url for url in locations)
    assert "https://hawatch.ir/points" not in locations
    assert "https://hawatch.ir/routes" not in locations
    assert "https://hawatch.ir/points/" not in locations
    assert "https://hawatch.ir/routes/" not in locations
    assert sum("/points/" in url for url in locations) == len(expected_points)
    assert sum("/routes/" in url for url in locations) == len(expected_routes)
    url_nodes = root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url")
    lastmods = {
        node.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text: node.find(
            "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod"
        )
        for node in url_nodes
    }
    assert lastmods["https://hawatch.ir/"] is None
    assert all(lastmods[url] is not None for url in expected_points | expected_routes | {"https://hawatch.ir/destinations"})
    for url in expected_points | expected_routes | {"https://hawatch.ir/destinations"}:
        assert lastmods[url].text.endswith("Z")
        parsed = datetime.fromisoformat(lastmods[url].text.replace("Z", "+00:00"))
        assert parsed.tzinfo == dt_timezone.utc


@pytest.mark.django_db
def test_sitemap_lastmod_uses_successful_point_forecast_and_catalog_fallback(api_client, seeded):
    point = WeatherPoint.objects.get(slug="azadkouh")
    forecast_at = datetime(2026, 9, 10, 7, 30, tzinfo=dt_timezone.utc)
    catalog_at = datetime(2026, 9, 8, 7, 30, tzinfo=dt_timezone.utc)
    WeatherPoint.objects.filter(pk=point.pk).update(updated_at=catalog_at)
    _persist_live_forecast_record(point, forecast_at)

    url = "https://hawatch.ir/points/azadkouh"
    assert _sitemap_lastmod(api_client.get("/api/v1/seo/sitemap.xml"), url) == forecast_at

    catalog_newer = datetime(2026, 9, 12, 7, 30, tzinfo=dt_timezone.utc)
    WeatherPoint.objects.filter(pk=point.pk).update(updated_at=catalog_newer)
    assert _sitemap_lastmod(api_client.get("/api/v1/seo/sitemap.xml"), url) == catalog_newer

    failed_at = datetime(2026, 9, 15, 7, 30, tzinfo=dt_timezone.utc)
    ForecastSnapshot.objects.create(
        provider="open-meteo",
        requested_at=failed_at,
        generated_at=failed_at,
        status=ForecastSnapshot.Status.FAILED,
        freshness=ForecastSnapshot.Freshness.STALE,
    )
    assert _sitemap_lastmod(api_client.get("/api/v1/seo/sitemap.xml"), url) == catalog_newer


@pytest.mark.django_db
def test_sitemap_route_lastmod_uses_latest_linked_point_forecast(api_client, seeded):
    route = Route.objects.get(slug="tochal-darband")
    route_at = datetime(2026, 9, 8, 7, 30, tzinfo=dt_timezone.utc)
    Route.objects.filter(pk=route.pk).update(updated_at=route_at)
    route_point = route.points.select_related("weather_point").first()
    forecast_at = datetime(2026, 9, 11, 7, 30, tzinfo=dt_timezone.utc)
    _persist_live_forecast_record(route_point.weather_point, forecast_at)

    url = "https://hawatch.ir/routes/tochal-darband"
    assert _sitemap_lastmod(api_client.get("/api/v1/seo/sitemap.xml"), url) == forecast_at


@pytest.mark.django_db
def test_sitemap_destinations_lastmod_ignores_forecast_and_tracks_catalog_changes(api_client, seeded):
    destination_at = datetime(2026, 9, 8, 7, 30, tzinfo=dt_timezone.utc)
    destination_points = publicly_visible_destinations()
    destination_points.update(updated_at=destination_at)

    destinations_url = "https://hawatch.ir/destinations"
    assert _sitemap_lastmod(api_client.get("/api/v1/seo/sitemap.xml"), destinations_url) == destination_at

    point = WeatherPoint.objects.get(slug="azadkouh")
    forecast_at = datetime(2026, 9, 12, 7, 30, tzinfo=dt_timezone.utc)
    _persist_live_forecast_record(point, forecast_at)

    # The point and its routes use the successful forecast timestamp, while
    # the catalog-only destinations hub remains unchanged.
    assert _sitemap_lastmod(api_client.get("/api/v1/seo/sitemap.xml"), "https://hawatch.ir/points/azadkouh") == forecast_at
    assert _sitemap_lastmod(api_client.get("/api/v1/seo/sitemap.xml"), destinations_url) == destination_at

    catalog_at = datetime(2026, 9, 15, 7, 30, tzinfo=dt_timezone.utc)
    WeatherPoint.objects.filter(pk=point.pk).update(updated_at=catalog_at)
    assert _sitemap_lastmod(api_client.get("/api/v1/seo/sitemap.xml"), destinations_url) == catalog_at

    removed_at = datetime(2026, 9, 16, 7, 30, tzinfo=dt_timezone.utc)
    WeatherPoint.objects.filter(pk=point.pk).update(is_active=False, updated_at=removed_at)
    assert _sitemap_lastmod(api_client.get("/api/v1/seo/sitemap.xml"), destinations_url) == removed_at


@pytest.mark.django_db
def test_destination_index_is_paginated_and_contains_only_primary_indexable_points(api_client, seeded):
    expected = set(publicly_visible_destinations().values_list("slug", flat=True))
    assert expected
    pages: list[set[str]] = []
    page_number = 1

    while True:
        response = api_client.get(f"/api/v1/destinations/?page={page_number}")
        assert response.status_code == 200
        payload = response.json()
        pagination = payload["pagination"]
        slugs = {item["slug"] for item in payload["destinations"]}
        assert len(slugs) <= DESTINATIONS_PAGE_SIZE
        assert all(item["seo_indexable"] for item in payload["destinations"])
        assert slugs.isdisjoint(set().union(*pages) if pages else set())
        pages.append(slugs)
        if not pagination["has_next"]:
            assert pagination["next_page"] is None
            assert pagination["next_href"] is None
            break
        assert pagination["next_page"] == page_number + 1
        assert pagination["next_href"] == f"/destinations/page/{page_number + 1}"
        page_number += 1

    assert set().union(*pages) == expected
    assert sum(len(page) for page in pages) == len(expected)
    assert api_client.get(f"/api/v1/destinations/?page={page_number + 1}").status_code == 400
    assert api_client.get("/api/v1/destinations/?page=not-a-page").status_code == 400


@pytest.mark.django_db
def test_robots_advertises_public_sitemap(api_client):
    response = api_client.get("/api/v1/seo/robots.txt")

    assert response.status_code == 200
    body = response.content.decode()
    assert "Allow: /" in body
    assert "Disallow: /api/" in body
    assert "Disallow: /admin/" in body
    assert "Sitemap: https://hawatch.ir/sitemap.xml" in body


@pytest.mark.django_db
def test_seed_is_idempotent(seeded):
    point_catalog_count = WeatherPoint.objects.count()
    route_count = Route.objects.count()
    point_count = RoutePoint.objects.count()
    forecast_count = ForecastRecord.objects.count()
    seed_demo_data(force=True)
    seed_demo_data(force=False)
    assert WeatherPoint.objects.count() == point_catalog_count
    assert Route.objects.count() == route_count
    assert RoutePoint.objects.count() == point_count
    assert ForecastRecord.objects.count() == forecast_count
    assert not (
        RoutePoint.objects.values("route", "sort_order")
        .annotate()
        .order_by()
        .distinct()
        .count()
        != point_count
    )


@pytest.mark.django_db
def test_point_forecast_shape_and_flags(api_client, seeded):
    today = now_tehran().date()
    response = api_client.get("/api/v1/points/tochal/forecast/", {"date": today.isoformat(), "period": "morning"})
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["timezone"] == "Asia/Tehran"
    assert body["meta"]["data_mode"] == "demo"
    assert body["meta"]["freshness"] in {"ready", "stale"}
    assert len(body["days"]) == 7
    assert body["days"][0]["is_yesterday"] is True
    assert body["days"][1]["is_today"] is True
    assert [item["hour"] for item in body["hourly"]] == [6, 8, 10]
    assert "is_past" in body["hourly"][0]
    assert "is_current" in body["hourly"][0]
    assert "is_future" in body["hourly"][0]
    noon = api_client.get(
        "/api/v1/points/tochal/forecast/",
        {"date": today.isoformat(), "period": "afternoon"},
    ).json()
    assert [item["hour"] for item in noon["hourly"]] == [12, 14, 16]


@pytest.mark.django_db
def test_deterministic_seed_same_hour(seeded):
    today = now_tehran().date()
    first = generate_reading(
        point_slug="tochal",
        climate_key="alpine",
        elevation_m=3964,
        local_date=today,
        hour=10,
    )
    second = generate_reading(
        point_slug="tochal",
        climate_key="alpine",
        elevation_m=3964,
        local_date=today,
        hour=10,
    )
    assert first == second
    other_hour = generate_reading(
        point_slug="tochal",
        climate_key="alpine",
        elevation_m=3964,
        local_date=today,
        hour=16,
    )
    other_day = generate_reading(
        point_slug="tochal",
        climate_key="alpine",
        elevation_m=3964,
        local_date=day_window(today)[0],
        hour=10,
    )
    assert first != other_hour or first["wind_speed_kmh"] != other_hour["wind_speed_kmh"] or first["temperature_c"] != other_hour["temperature_c"] or first["condition_label"] != other_hour["condition_label"]
    assert first != other_day


def test_demo_reading_rejects_unknown_climate_with_an_actionable_error():
    with pytest.raises(ValueError, match="Unsupported demo climate profile 'forest'"):
        generate_reading(
            point_slug="eskelim-parking",
            climate_key="forest",
            elevation_m=900,
            local_date=now_tehran().date(),
            hour=0,
        )


@pytest.mark.django_db
def test_route_forecast_start_and_speed(api_client, seeded):
    today = now_tehran().date()
    medium = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": today.isoformat(), "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    fast = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": today.isoformat(), "period": "morning", "start_time": "06:00", "speed": "سریع"},
    ).json()
    assert medium["timing_pending"] is False
    assert medium["timing_status"] == "estimated"
    assert medium["points"][0]["arrival_minutes"] == medium["start_minutes"]
    assert medium["points"][0]["time"] == medium["start_time"]
    assert "حدود" in medium["decision"]["title"]
    assert "timing pending" not in str(medium).lower()
    assert medium["decision"]["gear"]
    assert {"hiking-boots", "backpack", "water-bottle"}.issubset(medium["decision"]["gear"])

    kolakchal = api_client.get(
        "/api/v1/routes/tochal-kolakchal/forecast/",
        {"date": today.isoformat(), "period": "afternoon", "start_time": "17:00", "speed": "متوسط"},
    ).json()
    assert all(item["note"] == "" for item in kolakchal["points"])
    assert kolakchal["decision"]["critical_note"] == ""
    assert "Route-specific eastern parking" not in str(kolakchal)
    assert "piyazchal_pass and lezoon_east" not in str(kolakchal)

    assert fast["points"][-1]["arrival_minutes"] < medium["points"][-1]["arrival_minutes"]
    assert len(medium["points"]) == 6
    assert [item["slug"] for item in medium["points"]] == [
        "tochal-sarband-square",
        "tochal-pas-ghaleh-village",
        "tochal-shirpala-shelter",
        "tochal-amiri-shelter",
        "tochal-goleband-ridge",
        "tochal",
    ]
    assert {item["slug"] for item in medium["route"]["siblings"]} == {
        "tochal-velenjak",
        "tochal-kolakchal",
        "tochal-shahrestanak",
        "tochal-ahar",
    }

    # Current point-only catalogs expose only their active route graph.
    estimated = api_client.get(
        "/api/v1/routes/gahar-dorud/forecast/",
        {"date": today.isoformat(), "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    estimated_fast = api_client.get(
        "/api/v1/routes/gahar-dorud/forecast/",
        {"date": today.isoformat(), "period": "morning", "start_time": "06:00", "speed": "سریع"},
    ).json()
    assert estimated["timing_pending"] is False
    assert estimated["points"][0]["time"] == estimated["start_time"]
    assert estimated_fast["points"][-1]["arrival_minutes"] < estimated["points"][-1]["arrival_minutes"]


@pytest.mark.django_db
def test_point_fields_have_single_gist_index(seeded):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tablename, COUNT(*) AS gist_count
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexdef ILIKE '%USING gist%'
              AND tablename IN (
                'routes_route',
                'routes_routepoint',
                'forecasts_weatherpoint'
              )
            GROUP BY tablename
            ORDER BY tablename
            """
        )
        rows = {name: count for name, count in cursor.fetchall()}
    assert rows == {
        "forecasts_weatherpoint": 1,
        "routes_route": 1,
        "routes_routepoint": 1,
    }


@pytest.mark.django_db
def test_search_and_stale_flag(api_client, seeded):
    found = api_client.get("/api/v1/points/", {"query": "توچال"}).json()
    assert found["results"][0]["slug"] == "tochal"
    empty = api_client.get("/api/v1/points/", {"query": "xyz-not-a-place"}).json()
    assert empty["empty"] is True
    missing = api_client.get("/api/v1/points/unknown-place/")
    assert missing.status_code == 404


@pytest.mark.django_db
def test_point_forecast_pas_ghaleh(api_client, seeded):
    today = now_tehran().date()
    response = api_client.get(
        "/api/v1/points/tochal-pas-ghaleh-village/forecast/",
        {"date": today.isoformat(), "period": "morning"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["point"]["slug"] == "tochal-pas-ghaleh-village"
    assert body["point"]["name"] == "روستای پس‌قلعه"
    assert body["point"]["latitude"] == pytest.approx(35.8361950, rel=1e-4)
    assert body["point"]["longitude"] == pytest.approx(51.4233411, rel=1e-4)
    assert body["point"]["elevation_m"] == 1936
    assert "arrival_minutes" not in body["point"]
    assert "route_title" not in body["point"]
    assert len(body["hourly"]) == 3
    assert any(item["slug"] == "tochal-darband" for item in body["related_routes"])


@pytest.mark.django_db
def test_search_suggestions_points(api_client, seeded):
    points = api_client.get("/api/v1/search/suggestions/", {"q": "تو"}).json()
    assert any(item["type"] == "point" and item["slug"] == "tochal" for item in points["results"])
    point = api_client.get("/api/v1/search/suggestions/", {"q": "پس"}).json()
    assert any(item["type"] == "point" and item["slug"] == "tochal-pas-ghaleh-village" for item in point["results"])
    shir = api_client.get("/api/v1/search/suggestions/", {"q": "شیر"}).json()
    assert any(item["type"] == "point" and item["slug"] == "tochal-shirpala-shelter" for item in shir["results"])


@pytest.mark.django_db
def test_search_matches_words_inside_point_names(api_client, seeded):
    # ``گهر`` is not the first word in ``دریاچهٔ گهر``. A later word must be searchable.
    gahar = api_client.get("/api/v1/search/suggestions/", {"q": "گهر"}).json()["results"]
    assert any(item["type"] == "point" and item["slug"] == "gahar" for item in gahar)
    # Route titles are intentionally not searchable; only points are valid result types.
    assert all(item["type"] == "point" for item in gahar)


@pytest.mark.django_db
def test_primary_destination_exposes_routes_when_endpoint_is_named_shore(api_client, seeded):
    body = api_client.get("/api/v1/points/gahar/forecast/").json()
    routes = {item["slug"] for item in body["related_routes"]}
    assert {"gahar-dorud", "gahar-aligudarz"} <= routes


@pytest.mark.django_db
def test_point_only_forecast_exposes_curated_similar_destinations(api_client, seeded):
    body = api_client.get("/api/v1/points/dizin-ski-resort/forecast/").json()

    assert body["related_routes"] == []
    assert body["related_destinations_title"] == "پیست‌های اسکی مشابه"
    assert [item["slug"] for item in body["related_destinations"]] == [
        "darbandsar-ski-resort",
        "tochal-ski-resort",
        "abali-ski-resort",
        "sabalan-alvares-ski-resort",
    ]


@pytest.mark.django_db
def test_point_list_search_uses_same_normalization(api_client, seeded):
    response = api_client.get("/api/v1/points/", {"query": "گهر"})
    assert response.status_code == 200
    assert "gahar" in [item["slug"] for item in response.json()["results"]]


@pytest.mark.django_db
def test_search_no_duplicate_tochal_point(api_client, seeded):
    results = api_client.get("/api/v1/search/suggestions/", {"q": "توچال"}).json()["results"]
    summit_points = [item for item in results if item["type"] == "point" and item["slug"] == "tochal"]
    assert len(summit_points) == 1

    pas_results = api_client.get("/api/v1/search/suggestions/", {"q": "پس"}).json()["results"]
    assert any(item["type"] == "point" and item["slug"] == "tochal-pas-ghaleh-village" for item in pas_results)


@pytest.mark.django_db
def test_search_alias_and_deduplication(api_client, seeded):
    from hawatch.modules.catalog.models import SearchIndexEntry
    from hawatch.modules.catalog.search import rebuild_search_index
    from hawatch.modules.forecasts.models import WeatherPoint

    WeatherPoint.objects.filter(slug="tochal-pas-ghaleh-village").update(aliases=["پسغلعه"])
    rebuild_search_index()
    assert SearchIndexEntry.objects.filter(
        weather_point_slug="tochal-pas-ghaleh-village",
        match_kind=SearchIndexEntry.MatchKind.ALIAS,
    ).exists()

    alias = api_client.get("/api/v1/search/suggestions/", {"q": "پسغل"}).json()
    pas_matches = [item for item in alias["results"] if item.get("slug") == "tochal-pas-ghaleh-village"]
    assert len(pas_matches) == 1
    assert pas_matches[0]["match_kind"] == "alias"

    shared = api_client.get("/api/v1/search/suggestions/", {"q": "پس"}).json()
    pas_slugs = [item["slug"] for item in shared["results"] if item["type"] == "point" and item["slug"] == "tochal-pas-ghaleh-village"]
    assert len(pas_slugs) == 1


@pytest.mark.django_db
def test_route_point_forecast_endpoint_is_removed(api_client, seeded):
    response = api_client.get(
        "/api/v1/routes/tochal-darband/points/tochal-pas-ghaleh-village/forecast/",
        {"date": now_tehran().date().isoformat(), "period": "morning"},
    )
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "bad_start",
    [
        "12:xx",
        "12:00:00",
        "25:00",
        "12:60",
        "not-a-time",
    ],
)
def test_route_forecast_malformed_start_time_returns_400_not_500(api_client, seeded, bad_start):
    response = api_client.get(
        "/api/v1/routes/tochal-darband/forecast/",
        {"date": "2026-08-28", "period": "morning", "start_time": bad_start},
    )
    assert response.status_code == 400
    assert response.status_code != 500
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == 400
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["message"]

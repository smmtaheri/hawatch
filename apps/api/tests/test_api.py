import pytest
from django.db import connection
from rest_framework.test import APIClient

from hawatch.common.time import day_window, now_tehran
from hawatch.integrations.weather.demo import generate_reading
from hawatch.modules.catalog.seed import seed_demo_data
from hawatch.modules.forecasts.models import ForecastRecord, WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seeded(db):
    return seed_demo_data(force=True)


@pytest.mark.django_db
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
    slugs = set(WeatherPoint.objects.filter(kind=WeatherPoint.Kind.PRIMARY).values_list("slug", flat=True))
    assert slugs == {"azadkouh", "darabad", "dorfak", "gahar", "hazar", "sabalan", "tar-lake", "tochal", "zarrinkuh"}
    route_slugs = set(Route.objects.values_list("slug", flat=True))
    assert "tochal-darband" in route_slugs
    assert {"gahar-dorud", "gahar-aligudarz"} <= route_slugs
    assert len(route_slugs) == 27
    assert Route.objects.filter(target_weather_point__slug="tochal").count() == 5
    assert RoutePoint.objects.filter(route__slug="tochal-darband").count() == 6


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

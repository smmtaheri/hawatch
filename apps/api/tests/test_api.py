import pytest
from django.db import connection
from rest_framework.test import APIClient

from hawatch.common.time import day_window, now_tehran
from hawatch.integrations.weather.demo import generate_reading
from hawatch.modules.catalog.seed import seed_demo_data
from hawatch.modules.destinations.models import Destination
from hawatch.modules.forecasts.models import ForecastRecord
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
def test_known_destinations_and_routes_exist(seeded):
    slugs = set(Destination.objects.values_list("slug", flat=True))
    assert slugs == {"touchal", "damavand", "daryasar", "jangal-abr", "maranjab", "gahar"}
    route_slugs = set(Route.objects.values_list("slug", flat=True))
    assert "touchal-darband" in route_slugs
    assert "daryasar-dohazar" in route_slugs
    assert "gahar-lake" in route_slugs
    assert "marnjab-reg" in route_slugs
    assert Route.objects.filter(destination__slug="touchal").count() == 5
    assert RoutePoint.objects.filter(route__slug="touchal-darband").count() == 6


@pytest.mark.django_db
def test_seed_is_idempotent(seeded):
    dest_count = Destination.objects.count()
    route_count = Route.objects.count()
    point_count = RoutePoint.objects.count()
    forecast_count = ForecastRecord.objects.count()
    seed_demo_data(force=True)
    seed_demo_data(force=False)
    assert Destination.objects.count() == dest_count
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
def test_destination_forecast_shape_and_flags(api_client, seeded):
    today = now_tehran().date()
    response = api_client.get("/api/v1/destinations/touchal/forecast/", {"date": today.isoformat(), "period": "morning"})
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["timezone"] == "Asia/Tehran"
    assert body["meta"]["data_mode"] == "demo"
    assert body["meta"]["freshness"] in {"ready", "stale"}
    assert len(body["days"]) == 7
    assert body["days"][0]["is_yesterday"] is True
    assert body["days"][1]["is_today"] is True
    assert [item["hour"] for item in body["hourly"]] == [2, 4, 6, 8, 10]
    assert "is_past" in body["hourly"][0]
    assert "is_current" in body["hourly"][0]
    assert "is_future" in body["hourly"][0]
    afternoon = api_client.get(
        "/api/v1/destinations/touchal/forecast/",
        {"date": today.isoformat(), "period": "afternoon"},
    ).json()
    assert [item["hour"] for item in afternoon["hourly"]] == [12, 14, 16]


@pytest.mark.django_db
def test_deterministic_seed_same_hour(seeded):
    today = now_tehran().date()
    first = generate_reading(
        point_slug="dest:touchal",
        climate_key="alpine",
        elevation_m=3964,
        local_date=today,
        hour=10,
    )
    second = generate_reading(
        point_slug="dest:touchal",
        climate_key="alpine",
        elevation_m=3964,
        local_date=today,
        hour=10,
    )
    assert first == second
    other_hour = generate_reading(
        point_slug="dest:touchal",
        climate_key="alpine",
        elevation_m=3964,
        local_date=today,
        hour=16,
    )
    other_day = generate_reading(
        point_slug="dest:touchal",
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
        "/api/v1/routes/touchal-darband/forecast/",
        {"date": today.isoformat(), "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    fast = api_client.get(
        "/api/v1/routes/touchal-darband/forecast/",
        {"date": today.isoformat(), "period": "morning", "start_time": "06:00", "speed": "سریع"},
    ).json()
    assert medium["timing_pending"] is True
    assert medium["points"][0]["arrival_minutes"] is None
    assert medium["points"][0]["time"] == "—"
    assert fast["points"][0]["arrival_minutes"] is None
    assert fast["points"][0]["time"] == "—"
    assert len(medium["points"]) == 6
    assert [item["slug"] for item in medium["points"]] == [
        "sarband",
        "pas_ghaleh",
        "shirpala",
        "amiri",
        "goleband",
        "tochal_summit",
    ]
    assert {item["slug"] for item in medium["route"]["siblings"]} == {
        "touchal-welanjak",
        "touchal-kalkchal",
        "touchal-shahrestanak",
        "touchal-ahar",
    }

    # Non-Tochal estimated routes still honor start/speed timing.
    estimated = api_client.get(
        "/api/v1/routes/daryasar-dohazar/forecast/",
        {"date": today.isoformat(), "period": "morning", "start_time": "06:00", "speed": "متوسط"},
    ).json()
    estimated_fast = api_client.get(
        "/api/v1/routes/daryasar-dohazar/forecast/",
        {"date": today.isoformat(), "period": "morning", "start_time": "06:00", "speed": "سریع"},
    ).json()
    assert estimated["timing_pending"] is False
    assert estimated["points"][0]["time"] == estimated["start_time"]
    assert estimated_fast["points"][-1]["arrival_minutes"] < estimated["points"][-1]["arrival_minutes"]
    assert estimated_fast["decision"]["finish"] != estimated["decision"]["finish"]


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
                'destinations_destination',
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
        "destinations_destination": 1,
        "forecasts_weatherpoint": 1,
        "routes_route": 1,
        "routes_routepoint": 1,
    }


@pytest.mark.django_db
def test_search_and_stale_flag(api_client, seeded):
    found = api_client.get("/api/v1/destinations/", {"query": "توچال"}).json()
    assert found["results"][0]["slug"] == "touchal"
    empty = api_client.get("/api/v1/destinations/", {"query": "xyz-not-a-place"}).json()
    assert empty["empty"] is True
    missing = api_client.get("/api/v1/destinations/unknown-place/")
    assert missing.status_code == 404

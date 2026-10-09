"""Regression gates for batching, authoritative planner parity and access."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from hawatch.api.v1.day_bundles import point_day_bundle, route_day_bundle
from hawatch.api.v1.serializers import route_forecast, _records_for_day
from hawatch.common.time import now_tehran, PERIOD_IDS, SPEED_TIME_FACTORS
from hawatch.modules.accounts.models import AccountProfile, Membership, ForecastAccessPolicy
from hawatch.modules.accounts.services import resolve_forecast_access
from hawatch.modules.forecasts.models import ForecastRecord, WeatherPoint
from hawatch.modules.routes.models import Route

pytestmark = pytest.mark.django_db


def access_for(client=None):
    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_user(username="bundle-parity")
    return resolve_forecast_access(request)


def test_every_supported_plan_matches_existing_serializer_including_midnight(seeded):
    policy = ForecastAccessPolicy.objects.select_related("default_authenticated_plan").get()
    policy.default_authenticated_plan.visible_days_from_yesterday = 6
    policy.default_authenticated_plan.save()
    access = access_for()
    route = Route.objects.select_related("target_weather_point", "origin_weather_point").get(slug="tochal-darband")
    day = now_tehran().date()
    bundle = route_day_bundle(route, selected_date=day, period="morning", start_minutes=480, speed="متوسط", access=access)
    assert len(bundle["plans"]) == 72
    assert bundle["coverage"]["to"] > f"{day}T23:00"
    for period in PERIOD_IDS:
        for pace in SPEED_TIME_FACTORS:
            for slot in bundle["periods"][period]["planner_slots"]:
                old = route_forecast(route, selected_date=day, period=period, start_minutes=slot, speed=pace)
                plan = bundle["plans"][f"{pace}:{slot}"]
                for key in ("decision", "stats", "hero"):
                    assert plan[key] == old[key], (period, pace, slot, key)
                for new, existing in zip(plan["points"], old["points"], strict=True):
                    assert new == {field: existing[field] for field in new}, (period, pace, slot)


def test_bulk_query_count_does_not_scale_with_choices(seeded):
    access = access_for()
    route = Route.objects.select_related("target_weather_point", "origin_weather_point").get(slug="tochal-darband")
    # Warm demo bucket; neither API changes runtime records in production.
    with CaptureQueriesContext(connection) as captured:
        bundle = route_day_bundle(route, selected_date=now_tehran().date(), period="morning", start_minutes=480, speed="متوسط", access=access)
    assert len(bundle["plans"]) == 72
    assert len(captured) <= 45, [query["sql"] for query in captured]
    forecast_reads = [query for query in captured if 'FROM "forecasts_forecastrecord"' in query["sql"]]
    assert len(forecast_reads) <= 4


def test_midnight_arrivals_never_receive_locked_day_weather(seeded):
    client = APIClient()
    day = now_tehran().date()+timedelta(days=7)
    body = client.get("/api/v1/routes/tochal-darband/forecast/day/", {"date": day.isoformat(), "period": "night", "start_time": "23:00"}).json()
    access_end = body["forecast_access"]["available_through"]
    found = False
    for plan in body["plans"].values():
        for point in plan["points"]:
            if point["arrival_at"] and point["arrival_at"][:10] > access_end:
                found = True
                assert not point["weather_available"]
                assert point["forecast_at"] is None
                assert point["temp"] is None
    assert found
    denied = client.get("/api/v1/routes/tochal-darband/forecast/day/", {"date": (day+timedelta(days=3)).isoformat()})
    assert denied.status_code == 403 and "plans" not in denied.json()
    assert denied["Cache-Control"] == "private, no-store"


def test_point_bundle_extrema_use_all_day_apparent_values_and_keeps_legacy_aliases(seeded):
    day = now_tehran().date()
    point = WeatherPoint.objects.get(slug="tochal")
    records = _records_for_day(point, day)
    records[0].apparent_temperature_c = -37
    records[0].temperature_c = 91
    records[0].save()
    body = APIClient().get("/api/v1/points/tochal/forecast/day/", {"date": day.isoformat()}).json()
    assert body["daily_summary"]["apparent_min_c"] == -37
    assert body["daily_summary"]["apparent_max_c"] == max(row.apparent_temperature_c for row in records)
    assert set(body["periods"]) == set(PERIOD_IDS)
    for period in body["periods"].values():
        for hour in period["hourly"]:
            assert "temperature_c" in hour and "apparent_temperature_c" in hour
    assert body["data_revision"]


def test_empty_day_is_unavailable_instead_of_an_invented_temperature(seeded):
    day = now_tehran().date()-timedelta(days=20)
    body = APIClient().get("/api/v1/points/tochal/forecast/day/", {"date": day.isoformat()}).json()
    assert body["daily_summary"]["apparent_min_c"] is None
    assert body["daily_summary"]["apparent_max_c"] is None
    assert not any(period["hourly"] for period in body["periods"].values())


def test_real_paid_expiry_and_free_account_have_no_fake_remaining_days(seeded):
    client = APIClient()
    user = get_user_model().objects.create_user(username="expiry")
    profile = AccountProfile.objects.create(user=user, phone_e164="989000000222")
    client.force_login(user)
    assert client.get("/api/v1/auth/me/").json()["days_remaining"] is None
    from hawatch.modules.accounts.models import ForecastPlan
    plan = ForecastPlan.objects.get(code="professional")
    Membership.objects.create(profile=profile, plan=plan, expires_at=timezone.now()+timedelta(days=3, hours=1))
    body = client.get("/api/v1/auth/me/").json()
    assert body["days_remaining"] == 4 and body["expires_at"]
    assert client.get("/api/v1/points/tochal/forecast/day/").json()["cache_expires_at"] == body["expires_at"]


def test_search_route_opt_in_and_independent_catalog_filters(seeded):
    client = APIClient()
    assert all(item["type"] == "point" for item in client.get("/api/v1/search/suggestions/", {"q":"توچال"}).json()["results"])
    assert any(item["type"] == "route" for item in client.get("/api/v1/search/suggestions/", {"q":"توچال", "include_routes":"1"}).json()["results"])
    assert all("place_type" in item for item in client.get("/api/v1/search/suggestions/", {"q":"توچال", "include_routes":"1"}).json()["results"] if item["type"] == "point")
    assert client.get("/api/v1/routes/", {"query":"دربند"}).json()["routes"]
    assert not client.get("/api/v1/routes/", {"query":"هیچ‌مسیر"}).json()["routes"]
    assert not client.get("/api/v1/destinations/", {"query":"هیچ‌مقصد"}).json()["destinations"]


def test_qa_noindex_does_not_change_production_html(seeded):
    client = APIClient()
    assert client.get("/points/tochal")["X-Robots-Tag"] == "index,follow"
    with override_settings(HAWATCH_QA_NOINDEX=True, HAWATCH_NEW_DESIGN=True):
        response = client.get("/points/tochal")
        assert response["X-Robots-Tag"] == "noindex,nofollow"
        assert b"Vazirmatn-Regular" in response.content
    assert client.get("/points/tochal")["X-Robots-Tag"] == "index,follow"


def test_missing_apparent_provider_reading_is_not_replaced_by_temperature():
    from hawatch.integrations.weather.normalize import normalize_point_hourly
    payload = {"hourly": {"time": ["2026-10-01T08:00"], "temperature_2m": [25], "apparent_temperature": [None]}}
    assert normalize_point_hourly(payload, generated_at=timezone.now()) == []

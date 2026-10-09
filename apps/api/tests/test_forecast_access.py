from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from hawatch.common.time import now_tehran
from hawatch.modules.accounts.models import AccountProfile, ForecastAccessPolicy, ForecastPlan, Membership


@pytest.mark.django_db
def test_forecast_is_public_for_today_and_seven_following_days_despite_old_policy(seeded):
    policy = ForecastAccessPolicy.objects.get(singleton=1)
    policy.anonymous_visible_days_from_yesterday = 0
    policy.save()
    today = now_tehran().date()
    client = APIClient()
    body = client.get("/api/v1/points/tochal/forecast/").json()
    assert body["meta"]["selected_date"] == today.isoformat()
    assert body["forecast_access"]["available_through"] == (today+timedelta(days=7)).isoformat()
    assert len(body["days"]) == 8
    assert all(day["access"] == "available" for day in body["days"])
    for date in (today, today+timedelta(days=7)):
        assert client.get("/api/v1/points/tochal/forecast/", {"date":date.isoformat()}).status_code == 200
        assert client.get("/api/v1/routes/tochal-darband/forecast/", {"date":date.isoformat()}).status_code == 200


@pytest.mark.django_db
def test_allowlisted_login_is_a_server_session_and_exposes_free_plan(settings):
    settings.DEMO_AUTH_ALLOWED_PHONE = "989111111111"
    settings.DEMO_AUTH_FIXED_OTP = "2468"
    client = APIClient()
    response = client.post("/api/v1/auth/login/", {"phone": "09111111111", "code": "2468"}, format="json")
    assert response.status_code == 200
    assert response.json()["plan"]["title"] == "عضویت رایگان"
    assert "sessionid" in response.cookies
    assert client.get("/api/v1/auth/me/").status_code == 200
    assert client.post("/api/v1/auth/logout/", {}, format="json").status_code == 200
    assert client.get("/api/v1/auth/me/").json() == {"authenticated": False}


@pytest.mark.django_db
def test_plans_endpoint_exposes_runtime_config_without_account_data(seeded):
    client = APIClient()
    response = client.get("/api/v1/auth/plans/")

    assert response.status_code == 200
    assert response["Cache-Control"].startswith("no-store")
    body = response.json()
    assert {plan["tier"] for plan in body["plans"]} >= {"free", "paid"}
    professional = next(plan for plan in body["plans"] if plan["code"] == "professional")
    assert professional["duration_months"] == 3
    assert "accounts" not in body


@pytest.mark.django_db
def test_guest_session_is_small_private_json_without_cookies(api_client):
    response=api_client.get('/api/v1/auth/me/')
    assert response.status_code==200
    assert response.json()=={'authenticated':False}
    assert response['Content-Type'].startswith('application/json')
    assert len(response.content)<64
    assert 'no-store' in response['Cache-Control'] and 'private' in response['Cache-Control']
    assert not response.cookies

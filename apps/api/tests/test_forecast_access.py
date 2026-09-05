from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from hawatch.common.time import now_tehran
from hawatch.modules.accounts.models import AccountProfile, ForecastAccessPolicy, ForecastPlan, Membership


@pytest.mark.django_db
def test_anonymous_policy_zero_allows_only_yesterday_and_never_leaks_today(seeded):
    policy = ForecastAccessPolicy.objects.select_related("default_authenticated_plan").get(singleton=1)
    policy.anonymous_visible_days_from_yesterday = 0
    policy.save(update_fields=["anonymous_visible_days_from_yesterday"])
    today = now_tehran().date()
    client = APIClient()

    default_response = client.get("/api/v1/points/tochal/forecast/")
    assert default_response.status_code == 200
    assert default_response.json()["meta"]["selected_date"] == (today - timedelta(days=1)).isoformat()
    assert default_response.json()["forecast_access"]["available_through"] == (today - timedelta(days=1)).isoformat()

    denied = client.get("/api/v1/points/tochal/forecast/", {"date": today.isoformat(), "period": "morning"})
    assert denied.status_code == 403
    assert denied.json()["code"] == "login_required"
    assert "hourly" not in denied.json()
    assert denied["Cache-Control"] == "private, no-store"


@pytest.mark.django_db
def test_plan_is_enforced_server_side_for_point_and_route(seeded):
    policy = ForecastAccessPolicy.objects.select_related("default_authenticated_plan").get(singleton=1)
    policy.anonymous_visible_days_from_yesterday = 0
    policy.save(update_fields=["anonymous_visible_days_from_yesterday"])
    free = policy.default_authenticated_plan
    free.visible_days_from_yesterday = 1
    free.save(update_fields=["visible_days_from_yesterday"])
    paid = ForecastPlan.objects.create(code="plus", title="هواچ پلاس", tier="paid", visible_days_from_yesterday=3)
    user = get_user_model().objects.create_user(username="access-test")
    profile = AccountProfile.objects.create(user=user, phone_e164="989000000000")
    Membership.objects.create(profile=profile, plan=paid, source="test")
    today = now_tehran().date()

    client = APIClient()
    client.force_login(user)
    allowed = client.get("/api/v1/routes/tochal-darband/forecast/", {"date": (today + timedelta(days=2)).isoformat(), "period": "morning"})
    assert allowed.status_code == 200
    assert allowed.json()["forecast_access"]["plan_title"] == "هواچ پلاس"
    assert all(day["access"] == "available" for day in allowed.json()["days"][:4])

    too_far = client.get("/api/v1/routes/tochal-darband/forecast/", {"date": (today + timedelta(days=4)).isoformat(), "period": "morning"})
    assert too_far.status_code == 403
    assert too_far.json()["code"] == "plan_required"
    assert "points" not in too_far.json()


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
    assert client.get("/api/v1/auth/me/").status_code == 403

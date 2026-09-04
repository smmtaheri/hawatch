import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from hawatch.modules.analytics.models import PageViewEvent
from hawatch.modules.catalog.seed import seed_demo_data


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seeded(db):
    return seed_demo_data(force=True)


@pytest.mark.django_db
def test_page_view_is_privacy_preserving_and_idempotent(api_client, seeded):
    payload = {
        "page_type": "point",
        "slug": "tochal",
        "visitor_id": "visitor-0123456789abcdef",
        "navigation_id": "navigation-0123456789",
    }
    first = api_client.post("/api/v1/analytics/pageview/", payload, format="json")
    second = api_client.post("/api/v1/analytics/pageview/", payload, format="json")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    event = PageViewEvent.objects.get()
    assert event.page_slug == "tochal"
    assert payload["visitor_id"] not in event.visitor_hash
    assert len(event.visitor_hash) == 64


@pytest.mark.django_db
def test_page_view_accepts_routes_and_rejects_unknown_pages(api_client, seeded):
    response = api_client.post(
        "/api/v1/analytics/pageview/",
        {
            "page_type": "route",
            "slug": "tochal-darband",
            "visitor_id": "visitor-0123456789abcdef",
            "navigation_id": "navigation-route-1234",
        },
        format="json",
    )
    missing = api_client.post(
        "/api/v1/analytics/pageview/",
        {
            "page_type": "point",
            "slug": "does-not-exist",
            "visitor_id": "visitor-0123456789abcdef",
            "navigation_id": "navigation-route-5678",
        },
        format="json",
    )

    assert response.status_code == 201
    assert missing.status_code == 404
    assert PageViewEvent.objects.filter(page_type="route").count() == 1


@pytest.mark.django_db
def test_staff_and_bots_are_ignored(api_client, seeded):
    user = get_user_model().objects.create_user(username="staff", is_staff=True)
    api_client.force_authenticate(user=user)
    staff_response = api_client.post(
        "/api/v1/analytics/pageview/",
        {"page_type": "point", "slug": "tochal", "visitor_id": "visitor-0123456789abcdef", "navigation_id": "navigation-staff-1"},
        format="json",
    )
    api_client.force_authenticate(user=None)
    bot_response = api_client.post(
        "/api/v1/analytics/pageview/",
        {"page_type": "point", "slug": "tochal", "visitor_id": "visitor-0123456789abcdef", "navigation_id": "navigation-bot-1"},
        format="json",
        HTTP_USER_AGENT="Googlebot/2.1",
    )

    assert staff_response.status_code == 200
    assert staff_response.json()["ignored"] == "staff"
    assert bot_response.status_code == 200
    assert bot_response.json()["ignored"] == "bot"
    assert not PageViewEvent.objects.exists()


@pytest.mark.django_db
def test_admin_overview_contains_zero_view_pages_and_filters(seeded, client):
    user = get_user_model().objects.create_superuser(username="admin", password="safe-password")
    assert client.login(username="admin", password="safe-password")

    response = client.get(reverse("admin:analytics_pageviewevent_overview"), {"type": "point", "range": "today", "metric": "unique_visitors", "order": "asc"})

    assert response.status_code == 200
    assert "tochal" in response.content.decode()
    assert "Page View" in response.content.decode()

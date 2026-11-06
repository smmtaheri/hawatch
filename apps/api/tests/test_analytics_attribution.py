from datetime import timedelta
from urllib.parse import urlencode
import pytest
from django.http import QueryDict
from django.utils import timezone
from django.db import connection
from django.test.utils import CaptureQueriesContext
from hawatch.modules.analytics.models import (
    PageViewEvent,
    VisitSession,
    MonthlyPageViewAggregate,
)
from hawatch.modules.analytics.attribution import attribution, public_path
from hawatch.modules.analytics.reports import report_data


def report(**kwargs):
    return report_data(QueryDict(urlencode(kwargs)))


def event(at, visitor="a", session=None, navigation="unknown", slug="tochal"):
    return PageViewEvent.objects.create(
        page_type="point",
        page_slug=slug,
        visitor_hash=visitor * 64,
        navigation_id="nav-" + str(at.timestamp()) + slug + navigation,
        occurred_at=at,
        session=session,
        navigation_source=navigation,
    )


def payload(**extra):
    return dict(
        page_type="point",
        slug="tochal",
        visitor_id="visitor-0123456789abcdef",
        navigation_id="navigation-0123456789",
        **extra,
    )


@pytest.mark.django_db(transaction=True)
def test_upgrade_preserves_events_and_monthly_history(legacy_migration_database):
    from django.db.migrations.executor import MigrationExecutor

    before = [("analytics", "0002_monthlypageviewaggregate")]
    after = [
        (
            "analytics",
            "0003_analyticscoverage_pageviewevent_navigation_source_and_more",
        )
    ]
    executor = MigrationExecutor(connection)
    executor.migrate(before)
    old = executor.loader.project_state(before).apps
    old.get_model("analytics", "PageViewEvent").objects.create(
        page_type="point",
        page_slug="tochal",
        visitor_hash="a" * 64,
        navigation_id="old-navigation-1234",
    )
    old.get_model("analytics", "MonthlyPageViewAggregate").objects.create(
        month_start=timezone.now().date().replace(day=1),
        page_type="point",
        page_slug="tochal",
        page_views=42,
        unique_visitors=7,
    )
    executor = MigrationExecutor(connection)
    executor.migrate(after)
    new = executor.loader.project_state(after).apps
    preserved = new.get_model("analytics", "PageViewEvent").objects.get()
    assert preserved.navigation_id == "old-navigation-1234"
    assert preserved.navigation_source == "unknown" and preserved.session_id is None
    monthly = new.get_model("analytics", "MonthlyPageViewAggregate").objects.get()
    assert monthly.page_views == 42 and monthly.unique_visitors == 7
    assert not new.get_model("analytics", "VisitSession").objects.exists()
    coverage = new.get_model("analytics", "AnalyticsCoverage").objects.get()
    assert coverage.detailed_since < coverage.attribution_since <= timezone.now()


@pytest.mark.parametrize(
    "ref,tag,expected",
    [
        ("https://www.google.co.jp/search?q=private", "", "google"),
        ("https://l.instagram.com/private", "", "instagram"),
        ("https://t.me/private", "", "telegram"),
        ("https://google.com.evil.example/", "", "referral"),
        ("", "telegram", "telegram"),
        ("https://hawatch.ir/points/tochal", "", "direct_unknown"),
    ],
)
def test_source_evidence_is_bounded_and_server_derived(ref, tag, expected):
    d = attribution(
        {
            "referrer": ref,
            "utm_source": tag,
            "landing_path": "/points/tochal",
            "utm_campaign": "token=secret",
        }
    )
    assert d["source"] == expected
    assert "/" not in d["referrer_host"] and "?" not in d["referrer_host"]
    assert not d["campaign"]


def test_only_canonical_public_previous_paths_are_accepted():
    assert public_path("/points/tochal") == "/points/tochal"
    for bad in [
        "/admin/",
        "https://evil.test/",
        "/points/tochal?email=a@b.test",
        "//evil.test/",
        "/points/../../admin",
    ]:
        assert not public_path(bad)


@pytest.mark.django_db
def test_entry_and_page_share_one_hashed_session_with_stable_source(api_client, seeded):
    context = {
        "session_id": "session-0123456789abcd",
        "utm_source": "telegram",
        "utm_medium": "social",
        "utm_campaign": "channel",
        "landing_path": "/",
        "referrer": "https://t.me/private?secret=hidden",
    }
    for _ in range(2):
        assert (
            api_client.post(
                "/api/v1/analytics/pageview/",
                dict(payload(attribution=context), page_type="entry", slug="landing"),
                format="json",
            ).status_code
            == 201
        )
    assert not PageViewEvent.objects.exists()
    view_context = {
        **context,
        "utm_source": "google",
        "previous_path": "/",
        "navigation_source": "site_search",
    }
    assert (
        api_client.post(
            "/api/v1/analytics/pageview/",
            payload(attribution=view_context),
            format="json",
        ).status_code
        == 201
    )
    assert VisitSession.objects.count() == 1
    e = PageViewEvent.objects.get()
    s = e.session
    assert (
        s.source == "telegram" and s.referrer_host == "t.me" and s.landing_path == "/"
    )
    assert s.session_hash != context["session_id"]
    assert e.previous_path == "/" and e.navigation_source == "site_search"
    duplicate = api_client.post(
        "/api/v1/analytics/pageview/", payload(attribution=view_context), format="json"
    )
    assert duplicate.json()["duplicate"] and PageViewEvent.objects.count() == 1


@pytest.mark.django_db
def test_old_clients_and_malformed_optional_metadata_do_not_lose_views(
    api_client, seeded
):
    for index, meta in enumerate(
        [
            None,
            [],
            {
                "session_id": "bad",
                "previous_path": "https://private.example/?token=secret",
                "navigation_source": "nonsense",
            },
            {"navigation_source": []},
            {"navigation_source": {}},
        ]
    ):
        p = payload(attribution=meta)
        p["navigation_id"] += "-" + str(index)
        assert (
            api_client.post("/api/v1/analytics/pageview/", p, format="json").status_code
            == 201
        )
    assert PageViewEvent.objects.count() == 5
    assert not VisitSession.objects.exists()
    assert not PageViewEvent.objects.exclude(previous_path="").exists()


@pytest.mark.django_db
def test_attribution_can_be_disabled_without_stopping_old_page_counts(
    api_client, seeded, settings
):
    settings.ANALYTICS_ATTRIBUTION_ENABLED = False
    p = payload(
        attribution={
            "session_id": "session-0123456789abcd",
            "landing_path": "/points/tochal",
        }
    )
    assert (
        api_client.post("/api/v1/analytics/pageview/", p, format="json").status_code
        == 201
    )
    assert PageViewEvent.objects.count() == 1 and VisitSession.objects.count() == 0


@pytest.mark.django_db
def test_rolling_windows_are_not_calendar_days_and_boundaries_are_half_open():
    end = timezone.now() - timedelta(minutes=1)
    for hours in [0, 3, 23, 24, 25, 167, 168, 169, 576, 720, 721]:
        event(end - timedelta(hours=hours), visitor=str(hours % 10))
    for window, count in [("today", 3), ("24h", 3), ("7d", 6), ("30d", 9)]:
        r = report(range=window, until=end.isoformat(), group="source")
        assert r["summary"]["page_views"] == count, (window, r["summary"])
    assert (
        report(range="days", days=24, until=end.isoformat(), group="source")["summary"][
            "page_views"
        ]
        == 8
    )


@pytest.mark.django_db
def test_unique_totals_are_distinct_across_pages_days_and_groups():
    now = timezone.now()
    s = VisitSession.objects.create(
        visitor_hash="a" * 64, session_hash="s" * 64, source="google"
    )
    event(now - timedelta(hours=1), session=s, navigation="site_search")
    event(now - timedelta(hours=2), session=s, navigation="point", slug="damavand")
    event(now - timedelta(days=3), session=s, navigation="home")
    r = report(range="7d", group="navigation")
    assert r["summary"] == {"page_views": 3, "unique_visitors": 1, "sessions": 1}
    assert sum(row["unique_visitors"] for row in r["rows"]) == 3
    assert (
        report(range="7d", source="google", navigation="site_search", group="page")[
            "summary"
        ]["page_views"]
        == 1
    )


@pytest.mark.django_db
def test_home_only_entries_are_counted_without_inventing_point_views():
    VisitSession.objects.create(
        visitor_hash="a" * 64,
        session_hash="s" * 64,
        source="instagram",
        landing_path="/",
    )
    r = report(scope="entries", range="24h", group="source")
    assert r["summary"] == {"page_views": 1, "unique_visitors": 1, "sessions": 1}
    assert report(range="24h")["summary"]["page_views"] == 0


@pytest.mark.django_db
def test_historical_monthly_totals_remain_separate_and_never_invent_attribution():
    MonthlyPageViewAggregate.objects.create(
        page_type="point",
        page_slug="old-point",
        month_start=timezone.localdate().replace(day=1) - timedelta(days=31),
        page_views=10,
        unique_visitors=3,
    )
    event(timezone.now() - timedelta(days=100))
    r = report(range="all", group="source")
    assert r["summary"]["page_views"] == 11 and r["legacy_row"]["page_views"] == 10
    assert report(range="all", source="google")["summary"]["page_views"] == 0
    assert report(range="days", days=120)["summary"]["page_views"] == 1


@pytest.mark.django_db
def test_custom_range_validation_and_fixed_cutoff():
    end = timezone.now() - timedelta(minutes=1)
    start = end - timedelta(days=45)
    event(start)
    event(end)
    r = report(
        range="custom", start=start.isoformat(), end=end.isoformat(), group="time"
    )
    assert r["summary"]["page_views"] == 1 and r["end"] == end
    assert "until=" in r["query_string"]
    for params in [
        dict(range="days", days=-1),
        dict(range="custom"),
        dict(range="custom", start=end.isoformat(), end=start.isoformat()),
        dict(scope="entries", navigation="site_search"),
    ]:
        assert report(**params)["summary"] is None


@pytest.mark.django_db
def test_report_query_count_does_not_grow_per_source_row():
    for i in range(50):
        s = VisitSession.objects.create(
            visitor_hash=str(i).zfill(64),
            session_hash=str(i).zfill(64),
            source="referral",
            campaign="campaign-" + str(i),
        )
        event(timezone.now() - timedelta(minutes=i + 1), visitor=str(i % 10), session=s)
    with CaptureQueriesContext(connection) as q:
        r = report(range="7d", group="campaign")
    assert len(r["rows"]) == 50
    assert len(q) <= 6


@pytest.mark.django_db
def test_admin_csv_and_invalid_filters_preserve_privacy_and_prevent_formula_injection(
    client,
):
    from django.contrib.auth import get_user_model
    from django.conf import settings
    from django.urls import reverse
    from django.test import override_settings

    user = get_user_model().objects.create_superuser(
        username="analytics-export", password=None
    )
    client.force_login(user)
    cookie = client.cookies.pop(settings.SESSION_COOKIE_NAME)
    client.cookies[settings.ADMIN_SESSION_COOKIE_NAME] = cookie.value
    s = VisitSession.objects.create(
        visitor_hash="a" * 64,
        session_hash="s" * 64,
        source="referral",
        campaign="-unsafe-campaign",
    )
    event(timezone.now() - timedelta(minutes=1), session=s)
    listing = client.get(reverse("admin:analytics_pageviewevent_changelist"))
    assert listing.status_code == 200
    assert "سایت دیگر" in listing.content.decode()
    assert "-unsafe-campaign" in listing.content.decode()
    url = reverse("admin:analytics_pageviewevent_overview")
    r = client.get(url, {"range": "7d", "group": "campaign", "export": "csv"})
    assert r.status_code == 200
    assert "'-unsafe-campaign" in r.content.decode()
    assert "private" in r["Cache-Control"] and "no-store" in r["Cache-Control"]
    assert r["X-Robots-Tag"] == "noindex,nofollow"
    assert (
        client.get(url, {"range": "days", "days": "-2", "export": "csv"}).status_code
        == 400
    )
    assert client.get(url, {"range": "days", "days": "-2"}).status_code == 200
    with override_settings(ANALYTICS_REPORT_TIMEOUT_MS=3000):
        assert client.get(url, {"range": "24h", "group": "source"}).status_code == 200
    # SET LOCAL must not leak a timeout onto reused public DB connections.
    with connection.cursor() as cursor:
        cursor.execute("SHOW statement_timeout")
        assert cursor.fetchone()[0] == "0"


@pytest.mark.django_db
def test_shared_link_preserves_campaign_without_changing_stored_planner(
    api_client, seeded
):
    from hawatch.modules.routes.models import Route, SharedRoutePlan
    from urllib.parse import urlsplit, parse_qs

    route = Route.objects.filter(is_active=True).first()
    plan = SharedRoutePlan.objects.create(
        code="analytics-share",
        route=route,
        date=timezone.localdate(),
        start_hour=7,
        speed="medium",
        expires_at=timezone.now() + timedelta(days=1),
    )
    r = api_client.get(
        "/p/" + plan.code,
        {
            "utm_source": "telegram",
            "utm_medium": "social",
            "utm_campaign": "channel",
            "start_time": "20:00",
            "email": "private@example.com",
        },
    )
    assert r.status_code == 302
    q = parse_qs(urlsplit(r["Location"]).query)
    assert q["utm_source"] == ["telegram"] and q["utm_campaign"] == ["channel"]
    assert q["start_time"] == ["07:00"] and q["speed"] == ["medium"]
    assert "email" not in q and r["Cache-Control"] == "no-store"

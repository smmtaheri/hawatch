import pytest
import json
import time
from uuid import uuid4
from copy import deepcopy
from django.core.cache import cache
from django.core.management.color import no_style
from django.db import connection, transaction
from freezegun import freeze_time
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from django.conf import settings
from hawatch.modules.catalog.seed import ensure_catalog, ensure_forecasts
from hawatch.modules.catalog.models import SearchIndexEntry
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route, RoutePoint
from hawatch.common.observability import metrics
from hawatch.common import shared_http_metrics

TEST_NOW = settings.TEST_REFERENCE_INSTANT
_ELAPSED_CLOCKS = {name: getattr(time, name) for name in ("monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns")}


@pytest.fixture(autouse=True)
def isolated_test_clock(request, monkeypatch):
    """Reset calendar time per test; elapsed-time budgets still advance normally."""
    if request.node.get_closest_marker("real_clock"):
        yield None
    else:
        # Ignore pytest's timer module, NOT all of pytest: freezegun checks
        # caller depth, and a broad ignore makes cache get/set see two clocks.
        with freeze_time(TEST_NOW, tick=True, ignore=["_pytest.timing", "xdist", "execnet"], real_asyncio=True) as clock:
            with monkeypatch.context() as elapsed:
                for name, function in _ELAPSED_CLOCKS.items():
                    elapsed.setattr(time, name, function)
                # Freezegun replaces the builtin time.time class attribute with
                # a Python function; keep it static so DRF does not bind self.
                elapsed.setattr(SimpleRateThrottle, "timer", staticmethod(time.time))
                yield clock


@pytest.fixture(autouse=True)
def isolated_test_cache():
    """A rolled-back DB must never reuse another test's cached payload/revision."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def isolated_test_metrics():
    """Counters and Redis circuit-breaker state are process globals, not fixtures."""
    for metric in metrics._metrics.values():
        metric.values.clear()
        metric.histograms.clear()
    shared_http_metrics._retry_after = 0


@pytest.fixture
def api_client():
    """Shared API client for tests outside their historical module fixtures."""

    return APIClient()


@pytest.fixture
def seeded(loaded_catalog):
    """Fresh weather and independent catalog rows for each consuming test."""

    return ensure_forecasts(settings.DEMO_SEED_VERSION, force=True)


@pytest.fixture(scope="session")
def catalog_rows(django_db_setup, django_db_blocker):
    """Run the real importer once, then roll it back; never seed every test DB."""
    models = (WeatherPoint, Route, RoutePoint, SearchIndexEntry)
    with django_db_blocker.unblock(), freeze_time(TEST_NOW, tick=True, ignore=["_pytest.timing", "xdist", "execnet"]), transaction.atomic():
        ensure_catalog(settings.DEMO_SEED_VERSION)
        rows = [(model, list(model.objects.all())) for model in models]
        transaction.set_rollback(True)
    return rows


@pytest.fixture
def loaded_catalog(catalog_rows, db):
    """Copy current catalog data, not mutable instances or cross-test DB state."""
    for model, rows in catalog_rows:
        model.objects.bulk_create(deepcopy(rows), batch_size=500)
    with connection.cursor() as cursor:
        for sql in connection.ops.sequence_reset_sql(no_style(), [model for model, _ in catalog_rows]):
            cursor.execute(sql)
        # Rolled-back fixtures leave planner statistics empty/stale. Populate
        # them for realistic joins instead of depending on test execution order.
        for model, _ in catalog_rows:
            cursor.execute(f"ANALYZE {connection.ops.quote_name(model._meta.db_table)}")
    return {point.slug: point for point in WeatherPoint.objects.all()}


@pytest.fixture
def assert_profile_distance():
    """Published distances must match the reviewed chain, at display precision."""
    profiles = json.loads((settings.FIXTURES_DIR / "route_descent_v1.json").read_text())["routes"]
    by_slug = {row["slug"]: row for row in profiles}

    def check(route):
        profile = by_slug[route["slug"]]
        assert profile["chain"] == route["points"]
        distance = profile["cumulative_distance_m"][-1] / 1000
        assert distance > 0
        assert route["distance_km"] == pytest.approx(distance, abs=0.05)
    return check


@pytest.fixture
def legacy_migration_database(transactional_db):
    """Historical migrations run forwards in an empty, disposable DB only."""
    original = connection.settings_dict["NAME"]
    temporary = "hawatch_legacy_test_" + uuid4().hex[:12]
    quoted = connection.ops.quote_name(temporary)
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE {quoted}")
    connection.close()
    connection.settings_dict["NAME"] = temporary
    try:
        yield connection
    finally:
        connection.close()
        connection.settings_dict["NAME"] = original
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE {quoted}")


@pytest.fixture(autouse=True)
def sitemap_storage(settings, tmp_path):
    settings.SITEMAP_ROOT = tmp_path / "sitemap"


@pytest.fixture
def published_sitemap(api_client):
    """Explicitly publish test DB mutations before reading the static endpoint."""
    from hawatch.modules.catalog.sitemap import publish_sitemap

    def get():
        publish_sitemap()
        return api_client.get("/api/v1/seo/sitemap.xml")
    return get

import pytest
from rest_framework.test import APIClient

from hawatch.modules.catalog.seed import seed_demo_data


@pytest.fixture(autouse=True)
def _enable_db_access_for_all_tests(db):
    pass


@pytest.fixture
def api_client():
    """Shared API client for tests outside their historical module fixtures."""

    return APIClient()


@pytest.fixture
def seeded(db):
    """Seed the deterministic catalog for tests that need public pages."""

    return seed_demo_data(force=True)

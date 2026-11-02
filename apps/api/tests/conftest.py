import pytest
from rest_framework.test import APIClient

from hawatch.modules.catalog.seed import seed_demo_data


@pytest.fixture
def api_client():
    """Shared API client for tests outside their historical module fixtures."""

    return APIClient()


@pytest.fixture
def seeded(db):
    """Seed the deterministic catalog for tests that need public pages."""

    return seed_demo_data(force=True)


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

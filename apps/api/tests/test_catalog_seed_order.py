from hawatch.modules.catalog.seed import ensure_catalog
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route


def test_bootstrap_orders_catalogs_before_shared_point_consumers(db):
    """A fresh database must not depend on fixture filename ordering."""

    ensure_catalog("hawatch-test-demo-v1")

    assert WeatherPoint.objects.filter(
        slug__in={"tochal-jamshidieh-park", "tochal-kolakchal-camp", "kolakchal"},
        is_active=True,
    ).count() == 3
    assert Route.objects.filter(slug="kolakchal-jamshidieh", is_active=True).exists()

"""Contracts for deterministic clocks and non-shared fixture state."""
from datetime import datetime

import pytest
from django.core.cache import cache
from django.utils import timezone

from hawatch.common.time import default_forecast_selection, now_tehran
from hawatch.modules.forecasts.models import WeatherPoint


@pytest.mark.parametrize("iteration", range(3))
def test_clock_and_cache_start_fresh_for_every_case(iteration, isolated_test_clock, settings):
    assert now_tehran().date() == datetime.fromisoformat(settings.TEST_REFERENCE_INSTANT).date()
    assert cache.get("test-only:isolation-sentinel") is None
    cache.set("test-only:isolation-sentinel", iteration)
    isolated_test_clock.move_to("2099-12-31T23:59:00+03:30")
    assert timezone.now().year == 2099
    day, period = default_forecast_selection(now_tehran())
    assert day == datetime(2099, 12, 31).date() and period == "night"


@pytest.mark.parametrize("iteration", range(2))
def test_catalog_copies_do_not_leak_mutations(loaded_catalog, iteration):
    point = WeatherPoint.objects.get(slug="tochal")
    assert point.page_name != "تغییر فقط در تست قبلی"
    point.page_name = "تغییر فقط در تست قبلی"
    point.save(update_fields=["page_name"])


def test_default_cache_is_not_inherited_from_runtime_redis(settings):
    assert settings.REDIS_URL == ""
    assert settings.CACHES["default"]["BACKEND"].endswith("LocMemCache")


def test_cache_expiry_uses_one_wall_clock_at_every_call_depth(isolated_test_clock):
    def nested(depth, action):
        return nested(depth - 1, action) if depth else action()

    nested(12, lambda: cache.set("test-only:deep-clock", "nested", 120))
    assert cache.get("test-only:deep-clock") == "nested"
    cache.set("test-only:direct-clock", "direct", 120)
    assert nested(12, lambda: cache.get("test-only:direct-clock")) == "direct"
    isolated_test_clock.tick(121)
    assert cache.get("test-only:deep-clock") is None
    assert nested(12, lambda: cache.get("test-only:direct-clock")) is None

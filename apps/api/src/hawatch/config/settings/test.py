"""Isolated settings for pytest; never inherit runtime provider values."""

import json
import os
from copy import deepcopy
from pathlib import Path

from .base import *  # noqa: F403

DEBUG = False
DEMO_DATA_ENABLED = True
DEMO_SEED_VERSION = "hawatch-test-demo-v1"
OPEN_METEO_BASE_URL = "http://open-meteo.invalid"
METRICS_REQUIRE_AUTH = False
HAWATCH_ENVIRONMENT = "test"
OBSERVABILITY_ENVIRONMENT = "test"
HAWATCH_LOG_DIR = Path(os.environ.get("HAWATCH_TEST_LOG_DIR", "/tmp/hawatch-test-logs"))
HAWATCH_LOG_FILE = str(HAWATCH_LOG_DIR / "api.jsonl")
LOGGING = deepcopy(LOGGING)  # noqa: F405
LOGGING["handlers"]["file_json"]["filename"] = HAWATCH_LOG_FILE
DATABASES["default"]["TEST"] = {"NAME": os.environ.get("POSTGRES_TEST_DB", "hawatch_test")}  # noqa: F405


def _test_forecast_point_slugs():
    """Keep demo forecast fixtures limited to catalogs used by API tests."""

    slugs = set()
    for filename in ("tochal_v1.json", "gahar_v1.json"):
        catalog = json.loads((FIXTURES_DIR / "catalog" / filename).read_text(encoding="utf-8"))  # noqa: F405
        for route in (catalog.get("routes") or {}).values():
            slugs.update(route.get("points") or [])
    return tuple(sorted(slugs))


DEMO_FORECAST_POINT_SLUGS = _test_forecast_point_slugs()

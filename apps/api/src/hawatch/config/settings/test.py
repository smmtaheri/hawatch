"""Isolated settings for pytest; never inherit runtime provider values."""

import os

from .base import *  # noqa: F403

DEBUG = False
DEMO_DATA_ENABLED = True
DEMO_SEED_VERSION = "hawatch-test-demo-v1"
OPEN_METEO_BASE_URL = "http://open-meteo.invalid"
METRICS_REQUIRE_AUTH = False
HAWATCH_ENVIRONMENT = "test"
HAWATCH_LOG_DIR = Path("/tmp/hawatch-test-logs")  # noqa: F405
HAWATCH_LOG_FILE = str(HAWATCH_LOG_DIR / "api.jsonl")
DATABASES["default"]["TEST"] = {"NAME": os.environ.get("POSTGRES_TEST_DB", "hawatch_test")}  # noqa: F405

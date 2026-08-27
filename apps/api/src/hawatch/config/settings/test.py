from .base import *  # noqa: F403

DEBUG = False
METRICS_REQUIRE_AUTH = False
HAWATCH_LOG_DIR = Path("/tmp/hawatch-test-logs")  # noqa: F405
HAWATCH_LOG_FILE = str(HAWATCH_LOG_DIR / "api.jsonl")

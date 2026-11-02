"""Small shared HTTP counters; Redis failure never fails an HTTP response."""
import json
import time
from functools import lru_cache

from django.conf import settings
from redis import Redis

NAMES = {"hawatch_http_requests_total", "hawatch_http_errors_total", "hawatch_http_request_duration_seconds"}
_retry_after = 0.0


@lru_cache(maxsize=4)
def _client(url):
    return Redis.from_url(url, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)


def _store():
    if not settings.SHARED_HTTP_METRICS or not settings.REDIS_URL or time.monotonic() < _retry_after:
        return None
    return _client(settings.REDIS_URL)


def _key():
    return settings.HTTP_METRICS_REDIS_KEY


def _field(name, labels):
    return json.dumps([name, sorted((labels or {}).items())], separators=(",", ":"))


def _unavailable():
    global _retry_after
    _retry_after = time.monotonic() + 10


def increment(name, value, labels):
    try:
        store = _store()
        if store is not None:
            store.hincrbyfloat(_key(), _field(name, labels), value)
    except Exception:
        _unavailable()


def observe(name, value, labels, buckets):
    try:
        store = _store()
        if store is None:
            return
        pipe = store.pipeline()
        for bucket in buckets:
            if value <= bucket:
                pipe.hincrbyfloat(_key(), _field(name + "_bucket", {**(labels or {}), "le": str(bucket)}), 1)
        pipe.hincrbyfloat(_key(), _field(name + "_bucket", {**(labels or {}), "le": "+Inf"}), 1)
        pipe.hincrbyfloat(_key(), _field(name + "_sum", labels), value)
        pipe.hincrbyfloat(_key(), _field(name + "_count", labels), 1)
        pipe.execute()
    except Exception:
        _unavailable()


def snapshot():
    try:
        store = _store()
        if store is None:
            return None
        result = []
        for field, value in store.hgetall(_key()).items():
            name, labels = json.loads(field)
            result.append((name, dict(labels), float(value)))
        return result
    except Exception:
        _unavailable()
        return None

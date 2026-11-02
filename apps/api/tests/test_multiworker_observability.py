import logging
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import os
import time
from pathlib import Path
from uuid import uuid4

import pytest
from django.test import override_settings

from hawatch.common.observability import MetricsRegistry, SafeTimedRotatingFileHandler
from hawatch.common import shared_http_metrics

pytestmark = pytest.mark.real_clock


def _write_logs(path, barrier, prefix):
    handler = SafeTimedRotatingFileHandler(path, when="midnight", utc=True, backupCount=6)
    handler.setFormatter(logging.Formatter("%(message)s"))
    barrier.wait(timeout=10)
    for i in range(80):
        record = logging.LogRecord("test", logging.INFO, "test", 1, f"{prefix}-{i}", (), None)
        handler.handle(record)
    handler.close()


def test_two_workers_rotate_shared_log_without_losing_records(tmp_path):
    path = tmp_path / "api.jsonl"
    path.write_text("previous-day\n")
    old = time.time() - 86400
    os.utime(path, (old, old))
    # pytest-xdist has background threads; fork can inherit their locked state.
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    children = [context.Process(target=_write_logs, args=(str(path), barrier, name)) for name in ("a", "b")]
    try:
        for child in children:
            child.start()
        for child in children:
            child.join(15)
            assert child.exitcode == 0
        paths = [path, *tmp_path.glob("api.jsonl.*")]
        lines = [line for file in paths for line in file.read_text().splitlines()]
        assert len(lines) == 161
        assert set(lines) == {"previous-day"} | {f"{name}-{i}" for name in ("a", "b") for i in range(80)}
        assert len(list(tmp_path.glob("api.jsonl.*"))) == 1
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
                child.join(5)


def _metric_worker(url, key):
    with override_settings(REDIS_URL=url, SHARED_HTTP_METRICS=True, HTTP_METRICS_REDIS_KEY=key):
        registry = MetricsRegistry()
        registry.counter("hawatch_http_requests_total", "test")
        for _ in range(100):
            registry.inc("hawatch_http_requests_total", labels={"method": "GET", "route": "test", "status": 200})


def test_http_counters_aggregate_across_processes():
    url = os.environ.get("HAWATCH_TEST_REDIS_URL")
    if not url:
        pytest.skip("Set HAWATCH_TEST_REDIS_URL to an isolated test Redis")
    key = "hawatch:test:metrics:" + uuid4().hex
    with override_settings(REDIS_URL=url, SHARED_HTTP_METRICS=True, HTTP_METRICS_REDIS_KEY=key):
        shared_http_metrics._retry_after = 0
        context = multiprocessing.get_context("spawn")
        children = [context.Process(target=_metric_worker, args=(url, key)) for _ in range(2)]
        try:
            for child in children:
                child.start()
            for child in children:
                child.join(15)
                assert child.exitcode == 0
            rows = shared_http_metrics.snapshot()
            assert rows == [("hawatch_http_requests_total", {"method": "GET", "route": "test", "status": 200}, 200.0)]
        finally:
            for child in children:
                if child.is_alive():
                    child.terminate()
                    child.join(5)
            shared_http_metrics._client(url).delete(key)


def test_redis_metrics_failure_falls_back_without_raising(monkeypatch):
    monkeypatch.setattr(shared_http_metrics, "_retry_after", 0)
    monkeypatch.setattr(shared_http_metrics, "_client", lambda _: (_ for _ in ()).throw(ConnectionError()))
    with override_settings(REDIS_URL="redis://unavailable.invalid", SHARED_HTTP_METRICS=True):
        registry = MetricsRegistry()
        registry.counter("hawatch_http_requests_total", "test")
        registry.inc("hawatch_http_requests_total")
        assert "hawatch_http_requests_total 1" in registry.render()
        assert registry.http_scope == "process"


def test_threaded_metric_updates_and_scrapes_preserve_exact_counts():
    registry = MetricsRegistry()
    registry.counter("threaded_counter", "test")
    registry.histogram("threaded_duration", "test", (1, 2))

    def update(index):
        for _ in range(200):
            registry.inc("threaded_counter")
            registry.observe("threaded_duration", 1)
            registry.inc("threaded_counter", labels={"worker": index})

    def scrape():
        for _ in range(200):
            assert "# TYPE threaded_counter counter" in registry.render()

    with ThreadPoolExecutor(max_workers=9) as pool:
        futures = [pool.submit(update, i) for i in range(8)] + [pool.submit(scrape)]
        for future in futures:
            future.result()
    rendered = registry.render().splitlines()
    assert "threaded_counter 1600" in rendered
    assert "threaded_duration_count 1600" in rendered
    assert "threaded_duration_sum 1600" in rendered

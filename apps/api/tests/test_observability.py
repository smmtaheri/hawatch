from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from hawatch.common.observability import (
    metrics,
    record_ingest_duration,
    record_ingest_points,
    record_ingest_retry,
    record_ingest_run,
)
from hawatch.jobs.retention import cleanup_log_files
from hawatch.modules.catalog.seed import seed_demo_data
from hawatch.modules.forecasts.models import ForecastRecord, ForecastSnapshot


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seeded(db):
    return seed_demo_data(force=True)


@pytest.mark.django_db
def test_metrics_expose_catalog_health_and_request_data(api_client, seeded):
    response = api_client.get(
        "/api/v1/health/live/",
        HTTP_X_REQUEST_ID="request-test-1",
        HTTP_X_TRACE_ID="trace-test-1",
    )
    assert response.status_code == 200
    assert response["X-Request-ID"] == "request-test-1"
    assert response["X-Trace-ID"] == "trace-test-1"

    metrics_response = api_client.get("/api/v1/metrics/")
    assert metrics_response.status_code == 200
    body = metrics_response.content.decode()
    assert "# TYPE hawatch_http_requests_total counter" in body
    assert "hawatch_catalog_destinations" in body
    assert "hawatch_catalog_routes" in body
    assert "hawatch_catalog_weather_points" in body
    assert 'hawatch_health_status{check="live"} 1' in body


def test_metrics_endpoint_fails_closed_when_auth_is_enabled(api_client, monkeypatch):
    monkeypatch.delenv("HAWATCH_METRICS_TOKEN_FILE", raising=False)
    monkeypatch.setenv("HAWATCH_METRICS_TOKEN", "test-metrics-token")
    with override_settings(METRICS_REQUIRE_AUTH=True, METRICS_TOKEN_FILE=""):
        assert api_client.get("/api/v1/metrics/").status_code == 401
        response = api_client.get(
            "/api/v1/metrics/",
            HTTP_AUTHORIZATION="Bearer test-metrics-token",
        )
    assert response.status_code == 200


@pytest.mark.django_db
def test_status_endpoint_reports_catalog_and_live_freshness(api_client, seeded):
    response = api_client.get("/api/v1/health/status/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "ok"
    assert body["postgis"] is True
    assert body["catalog"]["destinations"] >= 1
    assert body["catalog"]["routes"] >= 1
    assert body["catalog"]["weather_points"] >= 1
    assert body["forecast"]["latest_attempt_status"] is None


def test_status_endpoint_requires_the_metrics_token(api_client, monkeypatch):
    monkeypatch.delenv("HAWATCH_METRICS_TOKEN_FILE", raising=False)
    monkeypatch.setenv("HAWATCH_METRICS_TOKEN", "test-status-token")
    with override_settings(METRICS_REQUIRE_AUTH=True, METRICS_TOKEN_FILE=""):
        assert api_client.get("/api/v1/health/status/").status_code == 401
        response = api_client.get(
            "/api/v1/health/status/",
            HTTP_AUTHORIZATION="Bearer test-status-token",
        )
    assert response.status_code == 200


@pytest.mark.django_db
def test_retention_command_deletes_old_hourly_forecasts_but_keeps_recent(seeded):
    old = ForecastRecord.objects.first()
    old.generated_at = timezone.now() - timedelta(days=8)
    old.save(update_fields=["generated_at"])
    fallback = ForecastSnapshot.objects.create(
        provider="open-meteo",
        source="open-meteo-forecast",
        requested_at=old.generated_at,
        generated_at=old.generated_at,
        status=ForecastSnapshot.Status.SUCCESS,
        freshness=ForecastSnapshot.Freshness.STALE,
        point_count=1,
        requested_point_count=1,
        raw_response={"fallback": True},
        checksum="fallback-snapshot",
    )
    old.snapshot = fallback
    old.save(update_fields=["snapshot"])
    recent_pk = ForecastRecord.objects.exclude(pk=old.pk).values_list("pk", flat=True).first()

    call_command("cleanup_retention", "--skip-opensearch")

    assert ForecastRecord.objects.filter(pk=old.pk).exists()
    assert ForecastSnapshot.objects.filter(pk=fallback.pk).exists()
    assert ForecastRecord.objects.filter(pk=recent_pk).exists()


def test_rotated_log_retention_is_targeted(tmp_path):
    old = tmp_path / "api.jsonl.2020-01-01"
    recent = tmp_path / "api.jsonl.2026-08-27"
    ignored = tmp_path / "unrelated.txt"
    for path in (old, recent, ignored):
        path.write_text("{}\n", encoding="utf-8")
    old_time = (timezone.now() - timedelta(days=8)).timestamp()
    import os

    os.utime(old, (old_time, old_time))

    result = cleanup_log_files(log_dir=tmp_path)

    assert result["deleted"] == 1
    assert not old.exists()
    assert recent.exists()
    assert ignored.exists()


def test_ingest_metric_hooks_are_available():
    record_ingest_run("success", provider="test")
    record_ingest_points(3, "success", provider="test")
    record_ingest_retry("429", provider="test")
    record_ingest_duration(0.25, provider="test")
    body = metrics.render()
    assert 'hawatch_ingest_runs_total{mode="live",provider="test",status="success"} 1' in body
    assert 'hawatch_ingest_points_total{mode="live",provider="test",status="success"} 3' in body
    assert 'hawatch_ingest_retries_total{provider="test",reason="429"} 1' in body
    assert 'hawatch_ingest_duration_seconds_count{provider="test"} 1' in body

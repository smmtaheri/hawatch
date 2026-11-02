import fcntl
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from xml.etree import ElementTree

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection, transaction
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from hawatch.jobs.sitemap_scheduler import SitemapScheduler
from hawatch.modules.catalog.sitemap import (
    build_sitemap, publish_sitemap, read_sitemap_status, sitemap_root, validate_sitemap,
)
from hawatch.modules.catalog.sitemap_http import sitemap_response
from hawatch.modules.catalog.sitemap_refresh import DIRTY_KEY, request_sitemap_refresh
from hawatch.modules.forecasts.models import WeatherPoint


def xml_for(name="destinations"):
    return ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'<url><loc>https://hawatch.ir/{name}</loc></url></urlset>').encode()


def publish(content=None):
    with patch("hawatch.modules.catalog.sitemap.build_sitemap", return_value=(content or xml_for(), {"urls": 1})):
        return publish_sitemap()


@pytest.mark.django_db
def test_http_reads_no_database_and_supports_head_and_conditional_requests(django_assert_num_queries):
    publish()
    factory = RequestFactory()
    with django_assert_num_queries(0):
        get = sitemap_response(factory.get("/sitemap.xml"))
        head = sitemap_response(factory.head("/sitemap.xml"))
        conditional = sitemap_response(factory.get("/sitemap.xml", HTTP_IF_NONE_MATCH=get["ETag"]))
        modified = sitemap_response(factory.get("/sitemap.xml", HTTP_IF_MODIFIED_SINCE=get["Last-Modified"]))
    assert get.status_code == head.status_code == 200
    assert get.content == xml_for() and head.content == b""
    assert head["Content-Length"] == str(len(get.content))
    assert conditional.status_code == modified.status_code == 304
    assert conditional.content == b""
    assert sitemap_response(factory.post("/sitemap.xml")).status_code == 405


@pytest.mark.django_db
def test_api_missing_file_is_fast_noncacheable_error_without_database(api_client, django_assert_num_queries):
    with django_assert_num_queries(0):
        response = api_client.get("/api/v1/seo/sitemap.xml")
    assert response.status_code == 503
    assert response["Cache-Control"] == "no-store"
    assert response["Retry-After"] == "60"


@pytest.mark.django_db
def test_successful_api_read_is_same_artifact_without_database(api_client, django_assert_num_queries):
    publish()
    with django_assert_num_queries(0):
        response = api_client.get("/api/v1/seo/sitemap.xml")
    assert response.status_code == 200 and response.content == xml_for()


def test_unchanged_content_keeps_mtime_but_updates_check_status():
    first = publish()
    stamp = (sitemap_root() / "sitemap.xml").stat().st_mtime_ns
    second = publish()
    assert first["changed"] and not second["changed"]
    assert (sitemap_root() / "sitemap.xml").stat().st_mtime_ns == stamp
    assert second["last_successful_check_at"] >= first["last_successful_check_at"]
    assert second["last_content_change_at"] == first["last_content_change_at"]


@pytest.mark.parametrize("error", [RuntimeError("db timeout"), OSError("disk full")])
def test_failed_build_preserves_last_good_xml(error):
    first = publish()
    with patch("hawatch.modules.catalog.sitemap.build_sitemap", side_effect=error):
        with pytest.raises(type(error)):
            publish_sitemap()
    assert (sitemap_root() / "sitemap.xml").read_bytes() == xml_for()
    status = read_sitemap_status()
    assert status["status"] == "failed"
    assert status["last_successful_check_at"] == first["last_successful_check_at"]


def test_first_publication_failure_is_visible_without_inventing_success_time():
    with patch("hawatch.modules.catalog.sitemap.build_sitemap", side_effect=RuntimeError("db timeout")):
        with pytest.raises(RuntimeError):
            publish_sitemap()
    status = read_sitemap_status()
    assert status["status"] == "failed" and status["check_stale"]
    assert status["last_successful_check_at"] is None
    assert status["error_type"] == "RuntimeError"


def test_interrupted_atomic_replace_keeps_old_xml():
    publish()
    from hawatch.modules.catalog import sitemap
    replace = sitemap.os.replace

    def interrupt(source, target):
        if str(target).endswith("/sitemap.xml"):
            raise OSError("simulated interrupted publication")
        return replace(source, target)

    with patch.object(sitemap.os, "replace", side_effect=interrupt):
        with pytest.raises(OSError):
            publish(xml_for("routes"))
    assert (sitemap_root() / "sitemap.xml").read_bytes() == xml_for()
    assert not list(sitemap_root().glob(".sitemap-*"))


def test_invalid_new_xml_cannot_replace_valid_file():
    publish()
    with pytest.raises(ElementTree.ParseError):
        publish(b"broken xml")
    assert (sitemap_root() / "sitemap.xml").read_bytes() == xml_for()


def test_changed_file_keeps_previous_verified_version():
    publish()
    publish(xml_for("routes"))
    assert (sitemap_root() / "sitemap.previous.xml").read_bytes() == xml_for()
    assert (sitemap_root() / "sitemap.xml").read_bytes() == xml_for("routes")


def test_valid_publication_recovers_corrupt_artifact_without_backing_it_up():
    sitemap_root().mkdir(parents=True, exist_ok=True)
    (sitemap_root() / "sitemap.xml").write_bytes(b"invalid")
    publish()
    assert (sitemap_root() / "sitemap.xml").read_bytes() == xml_for()
    assert not (sitemap_root() / "sitemap.previous.xml").exists()


def test_status_detects_stopped_publisher(settings):
    from datetime import datetime, timedelta, timezone
    import json

    publish()
    status_file = sitemap_root() / "status.json"
    status = json.loads(status_file.read_text())
    status["last_successful_check_at"] = (datetime.now(timezone.utc) - timedelta(seconds=901)).isoformat()
    status_file.write_text(json.dumps(status))
    settings.SITEMAP_REFRESH_SECONDS = 300
    assert read_sitemap_status()["check_stale"]
    assert read_sitemap_status()["check_age_seconds"] >= 901
    assert (sitemap_root() / "sitemap.xml").exists()


def test_concurrent_builder_cannot_overwrite_owner():
    publish()
    with (sitemap_root() / ".build.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert publish(xml_for("routes"))["status"] == "busy"
    assert (sitemap_root() / "sitemap.xml").read_bytes() == xml_for()


def test_parallel_readers_only_receive_complete_documents():
    publish()
    first, second = xml_for(), xml_for("routes")
    factory = RequestFactory()

    def read(_):
        content = sitemap_response(factory.get("/sitemap.xml")).content
        assert content in (first, second)
        ElementTree.fromstring(content)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(read, i) for i in range(40)]
        publish(second)
        for future in futures:
            future.result()


@pytest.mark.django_db
def test_builder_has_one_forecast_aggregation_and_no_correlated_subquery(seeded):
    with CaptureQueriesContext(connection) as queries:
        content, counts = build_sitemap()
    forecast_queries = [q["sql"] for q in queries if 'FROM "forecasts_forecastrecord"' in q["sql"]]
    assert len(forecast_queries) == 1
    assert "MAX(" in forecast_queries[0] and "GROUP BY" in forecast_queries[0]
    assert "LIMIT 1" not in forecast_queries[0]
    validate_sitemap(content, expected_count=counts["urls"])


@pytest.mark.django_db(transaction=True)
def test_production_snapshot_is_readonly_and_query_timeout_preserves_xml(settings):
    from django.db import OperationalError
    from hawatch.modules.catalog.sitemap import _read_snapshot

    settings.SITEMAP_QUERY_TIMEOUT_MS = 100
    publish()

    def slow_build():
        with _read_snapshot():
            with connection.cursor() as cursor:
                cursor.execute("SHOW transaction_read_only")
                assert cursor.fetchone()[0] == "on"
                cursor.execute("SELECT pg_sleep(1)")

    with patch("hawatch.modules.catalog.sitemap.build_sitemap", side_effect=slow_build):
        with pytest.raises(OperationalError):
            publish_sitemap()
    assert (sitemap_root() / "sitemap.xml").read_bytes() == xml_for()
    with connection.cursor() as cursor:
        cursor.execute("SHOW transaction_read_only")
        assert cursor.fetchone()[0] == "off"


@pytest.mark.django_db
def test_periodic_reconciliation_observes_bulk_changes_without_redis_signal(seeded):
    point = WeatherPoint.objects.filter(is_active=True, seo_indexable=True).first()
    scheduler = SitemapScheduler(interval=300)
    with patch("hawatch.jobs.sitemap_scheduler.refresh_marker", return_value=None):
        scheduler.tick(0)
        assert f"/points/{point.slug}</loc>".encode() in (sitemap_root() / "sitemap.xml").read_bytes()
        WeatherPoint.objects.filter(pk=point.pk).update(seo_indexable=False)
        scheduler.tick(300)
    assert f"/points/{point.slug}</loc>".encode() not in (sitemap_root() / "sitemap.xml").read_bytes()


@pytest.mark.django_db
def test_scheduler_handles_new_marker_during_build_and_retries_failure():
    scheduler = SitemapScheduler()
    with patch("hawatch.jobs.sitemap_scheduler.refresh_marker", side_effect=["a", "b", "b", "b"]), \
         patch("hawatch.jobs.sitemap_scheduler.publish_sitemap", side_effect=[{"status": "ok"}, RuntimeError("db"), {"status": "ok"}]) as build:
        scheduler.tick(0)
        scheduler.tick(30)
        scheduler.tick(45)
        scheduler.tick(60)
    assert build.call_count == 3 and not scheduler.failed


@pytest.mark.django_db
def test_redis_failure_does_not_prevent_periodic_generation():
    with patch("hawatch.modules.catalog.sitemap_refresh.cache.get", side_effect=ConnectionError), \
         patch("hawatch.jobs.sitemap_scheduler.publish_sitemap", return_value={"status": "ok"}) as build:
        scheduler = SitemapScheduler(interval=300)
        scheduler.tick(0)
        scheduler.tick(300)
    assert build.call_count == 2


@pytest.mark.django_db
def test_refresh_hint_runs_only_after_commit(django_capture_on_commit_callbacks):
    cache.delete(DIRTY_KEY)
    with django_capture_on_commit_callbacks(execute=True):
        request_sitemap_refresh()
        assert cache.get(DIRTY_KEY) is None
    assert cache.get(DIRTY_KEY)


@pytest.mark.django_db
def test_failed_transaction_does_not_publish_refresh_hint():
    cache.delete(DIRTY_KEY)
    with pytest.raises(ValueError), transaction.atomic():
        request_sitemap_refresh()
        raise ValueError("rollback")
    assert cache.get(DIRTY_KEY) is None


@pytest.mark.django_db
def test_management_command_publishes_valid_snapshot(seeded):
    call_command("build_sitemap")
    assert read_sitemap_status()["counts"]["urls"] > 3

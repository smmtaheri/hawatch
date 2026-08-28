"""Persist Open-Meteo batches into ForecastSnapshot + normalized hourly rows."""

from __future__ import annotations

import hashlib
import json
import time
from contextlib import contextmanager
from datetime import timedelta
from threading import Lock
from typing import Iterator, Sequence

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone as dj_timezone

from hawatch.common.time import hour_bucket, now_tehran
from hawatch.common.observability import (
    record_ingest_duration,
    record_ingest_points,
    record_ingest_run,
)
from hawatch.integrations.weather.normalize import (
    extract_resolution,
    normalize_point_hourly,
    provider_resolution_is_acceptable,
    response_items,
)
from hawatch.integrations.weather.providers.open_meteo import (
    OpenMeteoProvider,
    ProviderPoint,
)
from hawatch.modules.forecasts.models import (
    ForecastPointResolution,
    ForecastRecord,
    ForecastSnapshot,
    WeatherPoint,
)

LIVE_SEED_VERSION = "open-meteo-live"
RAW_RETENTION_DAYS = 7
INGEST_LOCK_KEY = 0x48415741  # "HAWA"
_PROCESS_INGEST_LOCK = Lock()


class IngestLockError(RuntimeError):
    """Raised when another ingest run already holds the advisory lock."""


def _stale_after() -> timedelta:
    hours = int(getattr(settings, "FORECAST_STALE_AFTER_HOURS", 3))
    return timedelta(hours=hours)


def weather_points_to_provider_points(points: Sequence[WeatherPoint]) -> list[ProviderPoint]:
    return [
        ProviderPoint(
            id=point.slug,
            latitude=point.location.y,
            longitude=point.location.x,
            elevation_m=point.elevation_m,
            cell_selection=(
                "nearest"
                if point.status == WeatherPoint.Status.PROVISIONAL
                else None
            ),
        )
        for point in points
    ]


def checksum_payload(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def mark_stale_snapshots(*, older_than: timedelta | None = None) -> int:
    cutoff = dj_timezone.now() - (older_than or _stale_after())
    return ForecastSnapshot.objects.filter(
        freshness=ForecastSnapshot.Freshness.READY,
        generated_at__lt=cutoff,
    ).update(freshness=ForecastSnapshot.Freshness.STALE)


def latest_usable_snapshot(*, provider: str = "open-meteo") -> ForecastSnapshot | None:
    return (
        ForecastSnapshot.objects.filter(provider=provider, status__in=["success", "partial"])
        .order_by("-generated_at")
        .first()
    )


def latest_snapshot(*, provider: str = "open-meteo") -> ForecastSnapshot | None:
    return latest_usable_snapshot(provider=provider)


def snapshot_freshness(snapshot: ForecastSnapshot | None) -> str:
    if snapshot is None:
        return ForecastSnapshot.Freshness.STALE
    if snapshot.freshness == ForecastSnapshot.Freshness.STALE:
        return ForecastSnapshot.Freshness.STALE
    if snapshot.generated_at < dj_timezone.now() - _stale_after():
        return ForecastSnapshot.Freshness.STALE
    if snapshot.status == ForecastSnapshot.Status.PARTIAL:
        return ForecastSnapshot.Freshness.PARTIAL
    return snapshot.freshness


def cleanup_old_snapshots(*, keep_days: int = RAW_RETENTION_DAYS) -> int:
    """Delete raw snapshots older than keep_days, never removing the latest usable one."""
    cutoff = dj_timezone.now() - timedelta(days=keep_days)
    latest = latest_usable_snapshot()
    qs = ForecastSnapshot.objects.filter(generated_at__lt=cutoff)
    if latest is not None:
        qs = qs.exclude(pk=latest.pk)
    deleted, _ = qs.delete()
    return deleted


def _cell_selection_for_batches(batch_results: Sequence[dict]) -> str:
    selections = {str(batch.get("cell_selection") or "land") for batch in batch_results}
    return "+".join(sorted(selections)) or "land"


@contextmanager
def ingest_lock(*, lock_key: int = INGEST_LOCK_KEY) -> Iterator[None]:
    """Postgres advisory lock to prevent concurrent ingest runs.

    Covers the full caller critical section (provider fetch + persistence when used by
    ingest_weather_points). Always attempts unlock on exit, including exceptions.
    """
    # PostgreSQL advisory locks are re-entrant on one DB session. The process
    # lock makes nested/same-process calls fail as well, while the advisory
    # lock still protects separate workers/processes.
    if not _PROCESS_INGEST_LOCK.acquire(blocking=False):
        raise IngestLockError("Another Open-Meteo ingest is already running")
    acquired = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [lock_key])
            acquired = bool(cursor.fetchone()[0])
        if not acquired:
            raise IngestLockError("Another Open-Meteo ingest is already running")
        yield
    finally:
        if acquired:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [lock_key])
        _PROCESS_INGEST_LOCK.release()


@transaction.atomic
def persist_ingest(
    *,
    weather_points: Sequence[WeatherPoint],
    batch_results: Sequence[dict],
    catalog_version: str = "",
    provider: OpenMeteoProvider | None = None,
    duration_seconds: float | None = None,
) -> ForecastSnapshot:
    """Store raw batches, provider resolutions, and normalized hourly rows.

    - Replaces live rows only for weather points whose batch succeeded.
    - Keeps previous live rows for failed batches (usable as stale data).
    - On total failure, preserves previous usable snapshot/records and returns that snapshot.
    """
    provider = provider or OpenMeteoProvider()
    requested_at = dj_timezone.now()
    generated_at = requested_at
    raw_response = {"batches": list(batch_results)}
    digest = checksum_payload(raw_response)
    existing = (
        ForecastSnapshot.objects.filter(provider="open-meteo", checksum=digest, status=ForecastSnapshot.Status.SUCCESS)
        .order_by("-generated_at")
        .first()
    )
    if existing:
        existing.freshness = ForecastSnapshot.Freshness.READY
        existing.save(update_fields=["freshness"])
        mark_stale_snapshots()
        return existing

    previous_usable = latest_usable_snapshot()
    point_by_slug = {point.slug: point for point in weather_points}
    successful_point_ids: list[str] = []
    failed_batches = 0
    rejected_resolution_batches = 0
    hourly_rows: list[ForecastRecord] = []
    resolutions: list[ForecastPointResolution] = []
    forecast_times_by_point: dict[str, set] = {}
    valid_from = None
    valid_to = None
    bucket = hour_bucket(now_tehran())

    for batch in batch_results:
        status_code = int(batch.get("status_code") or 0)
        payload = batch.get("payload")
        items = response_items(payload)
        point_ids = batch.get("point_ids") or []
        elevation_requested = bool(batch.get("elevation_requested"))
        if status_code != 200 or len(items) != len(point_ids):
            failed_batches += 1
            continue
        paired_points = [point_by_slug.get(point_id) for point_id in point_ids]
        if any(
            point is None
            or not provider_resolution_is_acceptable(
                raw_point,
                requested_latitude=point.location.y,
                requested_longitude=point.location.x,
            )
            for point, raw_point in zip(paired_points, items, strict=True)
        ):
            # A response with no usable/nearby resolved coordinate must never be
            # persisted under a catalog point. Keep the previous usable rows.
            failed_batches += 1
            rejected_resolution_batches += 1
            continue
        for point_id, raw_point in zip(point_ids, items, strict=True):
            weather_point = point_by_slug.get(point_id)
            assert weather_point is not None
            successful_point_ids.append(point_id)
            resolved = extract_resolution(raw_point)
            resolutions.append(
                ForecastPointResolution(
                    weather_point=weather_point,
                    requested_latitude=weather_point.location.y,
                    requested_longitude=weather_point.location.x,
                    requested_elevation_m=weather_point.elevation_m,
                    elevation_requested=elevation_requested,
                    resolved_latitude=resolved["resolved_latitude"],
                    resolved_longitude=resolved["resolved_longitude"],
                    resolved_elevation_m=resolved["resolved_elevation_m"],
                    utc_offset_seconds=resolved["utc_offset_seconds"],
                    generationtime_ms=resolved["generationtime_ms"],
                    timezone_abbreviation=resolved["timezone_abbreviation"],
                )
            )
            point_rows = normalize_point_hourly(raw_point, generated_at=generated_at)
            if point_rows:
                forecast_times_by_point.setdefault(point_id, set()).update(
                    row["forecast_at"] for row in point_rows
                )
            for row in point_rows:
                valid_from = row["valid_from"] if valid_from is None else min(valid_from, row["valid_from"])
                valid_to = row["valid_to"] if valid_to is None else max(valid_to, row["valid_to"])
                hourly_rows.append(
                    ForecastRecord(
                        weather_point=weather_point,
                        forecast_at=row["forecast_at"],
                        valid_from=row["valid_from"],
                        valid_to=row["valid_to"],
                        generated_at=generated_at,
                        hour_bucket=bucket,
                        temperature_c=row["temperature_c"],
                        apparent_temperature_c=row["apparent_temperature_c"],
                        weather_code=row["weather_code"],
                        condition_label=row["condition_label"],
                        icon=row["icon"],
                        wind_speed_kmh=row["wind_speed_kmh"],
                        wind_gust_kmh=row["wind_gust_kmh"],
                        wind_direction_deg=row["wind_direction_deg"],
                        precipitation_probability=row["precipitation_probability"],
                        precipitation_mm=row["precipitation_mm"],
                        snowfall_cm=row["snowfall_cm"],
                        visibility_km=row["visibility_km"],
                        cloud_cover_pct=row["cloud_cover_pct"],
                        uv_index=row["uv_index"],
                        freezing_level_m=row["freezing_level_m"],
                        cloud_base_m=row["cloud_base_m"],
                        severity=row["severity"],
                        freshness=ForecastRecord.Freshness.READY,
                        data_mode="live",
                        source="open-meteo-forecast",
                        seed_version=LIVE_SEED_VERSION,
                        provider="open-meteo",
                    )
                )

    if not successful_point_ids:
        # Total failure: keep previous usable data; record a failed audit snapshot only.
        ForecastSnapshot.objects.create(
            provider="open-meteo",
            source="open-meteo-forecast",
            catalog_version=catalog_version,
            timezone_name="Asia/Tehran",
            models_param="best_match",
            cell_selection=_cell_selection_for_batches(batch_results),
            forecast_days=provider.forecast_days,
            past_days=provider.past_days,
            batch_size=provider.batch_size,
            point_count=0,
            requested_point_count=len(weather_points),
            retry_count=sum(max(0, int(batch.get("attempts", 1)) - 1) for batch in batch_results),
            duration_seconds=duration_seconds,
            status=ForecastSnapshot.Status.FAILED,
            freshness=ForecastSnapshot.Freshness.STALE,
            requested_at=requested_at,
            generated_at=generated_at,
            valid_from=None,
            valid_to=None,
            checksum=digest,
            raw_response=raw_response,
            notes=(
                f"failed_batches={failed_batches}; resolution_rejected={rejected_resolution_batches}; "
                f"preserved_previous={previous_usable.pk if previous_usable else None}"
            ),
        )
        if previous_usable is not None:
            previous_usable.freshness = ForecastSnapshot.Freshness.STALE
            previous_usable.save(update_fields=["freshness"])
            cleanup_old_snapshots()
            return previous_usable
        failed = ForecastSnapshot.objects.filter(checksum=digest, status=ForecastSnapshot.Status.FAILED).latest(
            "generated_at"
        )
        cleanup_old_snapshots()
        return failed
    if failed_batches:
        status = ForecastSnapshot.Status.PARTIAL
        freshness = ForecastSnapshot.Freshness.PARTIAL
    else:
        status = ForecastSnapshot.Status.SUCCESS
        freshness = ForecastSnapshot.Freshness.READY

    snapshot = ForecastSnapshot.objects.create(
        provider="open-meteo",
        source="open-meteo-forecast",
        catalog_version=catalog_version,
        timezone_name="Asia/Tehran",
        models_param="best_match",
        cell_selection=_cell_selection_for_batches(batch_results),
        forecast_days=provider.forecast_days,
        past_days=provider.past_days,
        batch_size=provider.batch_size,
        point_count=len(successful_point_ids),
        requested_point_count=len(weather_points),
        retry_count=sum(max(0, int(batch.get("attempts", 1)) - 1) for batch in batch_results),
        duration_seconds=duration_seconds,
        status=status,
        freshness=freshness,
        requested_at=requested_at,
        generated_at=generated_at,
        valid_from=valid_from,
        valid_to=valid_to,
        checksum=digest,
        raw_response=raw_response,
        notes=(
            ""
            if status == ForecastSnapshot.Status.SUCCESS
            else f"failed_batches={failed_batches}; resolution_rejected={rejected_resolution_batches}"
        ),
    )

    for resolution in resolutions:
        resolution.snapshot = snapshot
    ForecastPointResolution.objects.bulk_create(resolutions, batch_size=500)

    succeeded_points = [point_by_slug[slug] for slug in successful_point_ids if slug in point_by_slug]
    if hourly_rows and succeeded_points:
        for row in hourly_rows:
            row.snapshot = snapshot
        # Upsert only the points returned successfully by this run. The whole
        # operation is inside the transaction above, so a persistence error
        # leaves the previous usable rows untouched.
        ForecastRecord.objects.bulk_create(
            hourly_rows,
            batch_size=1000,
            update_conflicts=True,
            update_fields=[
                "snapshot",
                "valid_from",
                "valid_to",
                "generated_at",
                "hour_bucket",
                "temperature_c",
                "apparent_temperature_c",
                "weather_code",
                "condition_label",
                "icon",
                "wind_speed_kmh",
                "wind_gust_kmh",
                "wind_direction_deg",
                "precipitation_probability",
                "precipitation_mm",
                "snowfall_cm",
                "visibility_km",
                "cloud_cover_pct",
                "uv_index",
                "freezing_level_m",
                "cloud_base_m",
                "severity",
                "freshness",
                "data_mode",
                "source",
                "provider",
            ],
            unique_fields=["weather_point", "forecast_at", "seed_version"],
        )
        # Remove hours that disappeared from a successful point's new window.
        # This runs after the upsert but remains inside the transaction, so an
        # exception still restores both the old and newly upserted rows.
        for point_id, forecast_times in forecast_times_by_point.items():
            ForecastRecord.objects.filter(
                weather_point=point_by_slug[point_id],
                data_mode="live",
                provider="open-meteo",
                seed_version=LIVE_SEED_VERSION,
            ).exclude(forecast_at__in=forecast_times).delete()

    mark_stale_snapshots()
    cleanup_old_snapshots()
    return snapshot


def ingest_weather_points(
    points: Sequence[WeatherPoint],
    *,
    provider: OpenMeteoProvider | None = None,
    catalog_version: str = "",
    acquire_lock: bool = True,
) -> ForecastSnapshot:
    provider = provider or OpenMeteoProvider()
    started = time.monotonic()

    def _run() -> ForecastSnapshot:
        provider_points = weather_points_to_provider_points(points)
        results = provider.fetch_all(provider_points)
        serialized = []
        for result in results:
            serialized.append(
                {
                    "point_ids": [point.id for point in result.points],
                    "status_code": result.status_code,
                    "payload": result.payload,
                    "elevation_requested": result.elevation_requested,
                    "cell_selection": result.cell_selection,
                    "url": result.url,
                    "attempts": result.attempts,
                }
            )
        return persist_ingest(
            weather_points=points,
            batch_results=serialized,
            catalog_version=catalog_version,
            provider=provider,
            duration_seconds=time.monotonic() - started,
        )

    try:
        if acquire_lock:
            with ingest_lock():
                snapshot = _run()
        else:
            snapshot = _run()
    except Exception:
        record_ingest_run("failed", provider="open-meteo")
        raise
    finally:
        record_ingest_duration(time.monotonic() - started, provider="open-meteo")
    record_ingest_run(snapshot.status, provider="open-meteo")
    if snapshot.point_count:
        record_ingest_points(snapshot.point_count, "success", provider="open-meteo")
    failed_points = max(0, snapshot.requested_point_count - snapshot.point_count)
    if failed_points:
        record_ingest_points(failed_points, "failed", provider="open-meteo")
    return snapshot


def ingest_tochal_catalog(*, provider: OpenMeteoProvider | None = None) -> ForecastSnapshot:
    from hawatch.modules.catalog.catalog import load_catalog_file

    catalog_version = load_catalog_file()["catalog_version"]
    return ingest_catalog(catalog_version, provider=provider)


def ingest_catalog(catalog_version: str, *, provider: OpenMeteoProvider | None = None) -> ForecastSnapshot:
    """Fetch the exact versioned catalog; never mix points from other destinations."""
    points = list(
        WeatherPoint.objects.filter(catalog_version=catalog_version, data_mode="live")
        .exclude(slug__startswith="dest:")
        .order_by("slug")
    )
    if not points:
        raise ValueError(f"No live WeatherPoints found for catalog version: {catalog_version}")
    return ingest_weather_points(points, provider=provider, catalog_version=catalog_version)

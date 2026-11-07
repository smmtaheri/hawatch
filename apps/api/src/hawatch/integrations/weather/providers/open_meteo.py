"""Open-Meteo forecast provider adapter.

API request handlers must never call this module. Use management commands / jobs only.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Any, Sequence
from datetime import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone as dj_timezone

from hawatch.common.observability import record_ingest_retry
from hawatch.integrations.weather.transport import WeatherHttpTransport
from hawatch.integrations.weather.rate_limit import WeatherQuotaUnavailable, retry_after_seconds, quota_retry_delay

log = logging.getLogger(__name__)

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "rain",
    "snowfall",
    "freezing_level_height",
    "weather_code",
    "visibility",
    "uv_index",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]

DEFAULT_BATCH_SIZE = 25
DEFAULT_FORECAST_DAYS = 10
# Ten days cover the eight selectable starts plus normal route arrival tails.
# Retained prior ingestion records supply historical hazard context.
DEFAULT_PAST_DAYS = 0
DEFAULT_TIMEZONE = "Asia/Tehran"
DEFAULT_MODELS = "best_match"
FALLBACK_MODELS = "ecmwf_ifs"
DEFAULT_CELL_SELECTION = "land"
NULL_ELEVATION_CELL_SELECTION = "nearest"
USER_AGENT = "hawatch-openmeteo/1.0"
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
BASE_BACKOFF_SECONDS = 0.5


def _forecast_endpoint(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("?/")
    if cleaned.endswith("/v1/forecast"):
        return cleaned
    return f"{cleaned}/v1/forecast"


@dataclass(frozen=True)
class ProviderPoint:
    id: str
    latitude: float
    longitude: float
    elevation_m: int | None = None
    # Provisional catalog elevations should not move the request to a distant
    # land cell merely to match an uncertain height.
    cell_selection: str | None = None


@dataclass
class BatchResult:
    points: list[ProviderPoint]
    status_code: int
    payload: Any
    elevation_requested: bool
    url: str
    attempts: int = 1
    cell_selection: str = DEFAULT_CELL_SELECTION
    models: str = DEFAULT_MODELS
    received_at: datetime | None = None


class OpenMeteoProvider:
    """Batch forecast client matching the hawatch Open-Meteo probe parameters."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        batch_size: int | None = None,
        forecast_days: int | None = None,
        past_days: int | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int = MAX_RETRIES,
        opener=None,
        sleeper=None,
        requester=None,
        rate_limiter=None,
    ) -> None:
        self.base_url = _forecast_endpoint(
            base_url or getattr(settings, "OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
        )
        # Older deployments can retain batch_size=100 in .env. Never let those
        # values silently restore large requests after this rollout.
        self.batch_size = min(DEFAULT_BATCH_SIZE, batch_size if batch_size is not None else int(
            getattr(settings, "OPEN_METEO_BATCH_SIZE", DEFAULT_BATCH_SIZE)))
        if self.batch_size <= 0:
            raise ValueError("Weather batch size must be positive")
        self.forecast_days = forecast_days or int(getattr(settings, "OPEN_METEO_FORECAST_DAYS", DEFAULT_FORECAST_DAYS))
        self.past_days = past_days if past_days is not None else int(getattr(settings, "OPEN_METEO_PAST_DAYS", DEFAULT_PAST_DAYS))
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self._sleeper = sleeper or time.sleep
        self.stop_reason = ""
        self._attempt_number = 1
        self._retry_after = None
        self._transport = WeatherHttpTransport(opener=opener, requester=requester, rate_limiter=rate_limiter)

    def split_batches(self, points: Sequence[ProviderPoint]) -> list[list[ProviderPoint]]:
        size = max(1, self.batch_size)
        return [list(points[i : i + size]) for i in range(0, len(points), size)]

    def partition_by_elevation(self, points: Sequence[ProviderPoint]) -> tuple[list[ProviderPoint], list[ProviderPoint]]:
        with_elevation = [point for point in points if point.elevation_m is not None]
        without_elevation = [point for point in points if point.elevation_m is None]
        return with_elevation, without_elevation

    def build_url(
        self,
        points: Sequence[ProviderPoint],
        *,
        include_elevation: bool,
        cell_selection: str = DEFAULT_CELL_SELECTION,
        models: str = DEFAULT_MODELS,
    ) -> str:
        params: dict[str, str] = {
            "latitude": ",".join(f"{point.latitude:.7f}" for point in points),
            "longitude": ",".join(f"{point.longitude:.7f}" for point in points),
            "timezone": DEFAULT_TIMEZONE,
            "models": models,
            "cell_selection": cell_selection,
            "forecast_days": str(self.forecast_days),
            "past_days": str(self.past_days),
            "hourly": ",".join(HOURLY_VARIABLES),
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "timeformat": "iso8601",
        }
        if include_elevation:
            if any(point.elevation_m is None for point in points):
                raise ValueError("Cannot request elevation for points with null catalog elevation")
            params["elevation"] = ",".join(str(int(point.elevation_m)) for point in points)
        return f"{self.base_url}?{urlencode(params)}"

    def _once(self, url: str) -> tuple[int, Any]:
        response = self._transport.get_json(
            url,
            timeout=self.timeout_seconds,
            user_agent=USER_AGENT,
            attempt=self._attempt_number,
        )
        self._retry_after = response.retry_after
        return response.status_code, response.payload

    def fetch_batch(
        self,
        points: Sequence[ProviderPoint],
        *,
        include_elevation: bool,
        cell_selection: str = DEFAULT_CELL_SELECTION,
        models: str = DEFAULT_MODELS,
    ) -> BatchResult:
        if not points:
            return BatchResult(
                points=[],
                status_code=200,
                payload=[],
                elevation_requested=include_elevation,
                url="",
                attempts=1,
                cell_selection=cell_selection,
                models=models,
            )
        url = self.build_url(points, include_elevation=include_elevation, cell_selection=cell_selection, models=models)
        attempts = 0
        status = 0
        payload: Any = {"transport_error": "not attempted"}
        if self.stop_reason:
            return BatchResult(list(points), 0, {"request_deferred": self.stop_reason},
                               include_elevation, url, 0, cell_selection, models)
        while attempts <= self.max_retries:
            self._attempt_number = attempts + 1
            self._retry_after = None
            try:
                status, payload = self._once(url)
            except WeatherQuotaUnavailable:
                self.stop_reason = "quota_coordinator_unavailable"
                payload = {"request_deferred": self.stop_reason}
                status = 0
                break
            attempts += 1
            if status == 200:
                break
            retryable = status in RETRYABLE_STATUS or status == 0
            if not retryable or attempts > self.max_retries:
                if status == 429:
                    # Do not turn quota exhaustion into a new model/proxy storm.
                    self.stop_reason = "provider_rate_limited"
                break
            retry_after = self._retry_after
            if isinstance(payload, dict):
                retry_after = max((v for v in [retry_after, retry_after_seconds(payload.get("retry_after")),
                                               retry_after_seconds(payload.get("Retry-After"))] if v is not None), default=None)
            delay = (quota_retry_delay(payload, retry_after, retry=attempts - 1) if status == 429
                     else retry_after if retry_after is not None
                     else BASE_BACKOFF_SECONDS * (2 ** (attempts - 1)))
            record_ingest_retry(
                "transport" if status == 0 else f"http_{status}",
                provider="open-meteo",
            )
            self._sleeper(delay if status == 429 or retry_after is not None else min(delay, 30.0))
        if self.stop_reason:
            log.warning("Weather collection deferred; preserving previous forecasts", extra={
                "event": "weather.collection_deferred", "reason": self.stop_reason,
                "point_count": len(points), "attempts": attempts,
            })
        return BatchResult(
            points=list(points),
            status_code=status,
            payload=payload,
            elevation_requested=include_elevation,
            url=url,
            attempts=attempts,
            cell_selection=cell_selection,
            models=models,
            received_at=dj_timezone.now() if status == 200 else None,
        )

    def fetch_all(self, points: Sequence[ProviderPoint], *, models: str = DEFAULT_MODELS) -> list[BatchResult]:
        with_elevation, without_elevation = self.partition_by_elevation(points)
        results: list[BatchResult] = []
        explicit_land = [point for point in with_elevation if point.cell_selection != NULL_ELEVATION_CELL_SELECTION]
        explicit_nearest = [point for point in with_elevation if point.cell_selection == NULL_ELEVATION_CELL_SELECTION]
        for batch in self.split_batches(explicit_land):
            results.append(self.fetch_batch(batch, include_elevation=True, cell_selection=DEFAULT_CELL_SELECTION, models=models))
        for batch in self.split_batches(explicit_nearest):
            results.append(
                self.fetch_batch(
                    batch,
                    include_elevation=True,
                    cell_selection=NULL_ELEVATION_CELL_SELECTION,
                    models=models,
                )
            )
        for batch in self.split_batches(without_elevation):
            # Without catalog elevation, prefer the geographically nearest grid cell.
            results.append(
                self.fetch_batch(
                    batch,
                    include_elevation=False,
                    cell_selection=NULL_ELEVATION_CELL_SELECTION,
                    models=models,
                )
            )
        return results

    def fetch_raw(self, latitude: float, longitude: float, **kwargs) -> dict:
        elevation = kwargs.get("elevation_m")
        point = ProviderPoint(id="single", latitude=latitude, longitude=longitude, elevation_m=elevation)
        result = self.fetch_batch(
            [point],
            include_elevation=elevation is not None,
            cell_selection=DEFAULT_CELL_SELECTION if elevation is not None else NULL_ELEVATION_CELL_SELECTION,
        )
        return {"status_code": result.status_code, "payload": result.payload, "url": result.url, "attempts": result.attempts}

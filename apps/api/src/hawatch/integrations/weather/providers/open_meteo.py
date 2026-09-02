"""Open-Meteo forecast provider adapter.

API request handlers must never call this module. Use management commands / jobs only.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from hawatch.common.observability import record_ingest_retry

HOURLY_VARIABLES = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "rain",
    "snowfall",
    "freezing_level_height",
    "weather_code",
    "visibility",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]

DEFAULT_BATCH_SIZE = 100
DEFAULT_FORECAST_DAYS = 7
# Keep the previous local day in the database from the preceding ingest, but
# do not ask Open-Meteo to fetch it again.  ``forecast_days=7`` then covers
# today through six days ahead.
DEFAULT_PAST_DAYS = 0
DEFAULT_TIMEZONE = "Asia/Tehran"
DEFAULT_MODELS = "best_match"
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
    ) -> None:
        self.base_url = _forecast_endpoint(
            base_url or getattr(settings, "OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
        )
        self.batch_size = batch_size or int(getattr(settings, "OPEN_METEO_BATCH_SIZE", DEFAULT_BATCH_SIZE))
        self.forecast_days = forecast_days or int(getattr(settings, "OPEN_METEO_FORECAST_DAYS", DEFAULT_FORECAST_DAYS))
        self.past_days = past_days if past_days is not None else int(getattr(settings, "OPEN_METEO_PAST_DAYS", DEFAULT_PAST_DAYS))
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self._opener = opener
        self._sleeper = sleeper or time.sleep

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
    ) -> str:
        params: dict[str, str] = {
            "latitude": ",".join(f"{point.latitude:.7f}" for point in points),
            "longitude": ",".join(f"{point.longitude:.7f}" for point in points),
            "timezone": DEFAULT_TIMEZONE,
            "models": DEFAULT_MODELS,
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
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            if self._opener is not None:
                response = self._opener(request, timeout=self.timeout_seconds)
                body = response.read().decode("utf-8")
                status = getattr(response, "status", 200)
            else:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    body = response.read().decode("utf-8")
                    status = response.status
            return status, json.loads(body)
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"raw_error": body}
            return error.code, parsed
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            return 0, {"transport_error": str(error)}

    def fetch_batch(
        self,
        points: Sequence[ProviderPoint],
        *,
        include_elevation: bool,
        cell_selection: str = DEFAULT_CELL_SELECTION,
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
            )
        url = self.build_url(points, include_elevation=include_elevation, cell_selection=cell_selection)
        attempts = 0
        status = 0
        payload: Any = {"transport_error": "not attempted"}
        while attempts <= self.max_retries:
            attempts += 1
            status, payload = self._once(url)
            if status == 200:
                break
            retryable = status in RETRYABLE_STATUS or status == 0
            if not retryable or attempts > self.max_retries:
                break
            retry_after = None
            if isinstance(payload, dict):
                retry_after = payload.get("retry_after") or payload.get("Retry-After")
            delay = float(retry_after) if retry_after is not None else BASE_BACKOFF_SECONDS * (2 ** (attempts - 1))
            record_ingest_retry(
                "transport" if status == 0 else f"http_{status}",
                provider="open-meteo",
            )
            self._sleeper(min(delay, 30.0))
        return BatchResult(
            points=list(points),
            status_code=status,
            payload=payload,
            elevation_requested=include_elevation,
            url=url,
            attempts=attempts,
            cell_selection=cell_selection,
        )

    def fetch_all(self, points: Sequence[ProviderPoint]) -> list[BatchResult]:
        with_elevation, without_elevation = self.partition_by_elevation(points)
        results: list[BatchResult] = []
        explicit_land = [point for point in with_elevation if point.cell_selection != NULL_ELEVATION_CELL_SELECTION]
        explicit_nearest = [point for point in with_elevation if point.cell_selection == NULL_ELEVATION_CELL_SELECTION]
        for batch in self.split_batches(explicit_land):
            results.append(self.fetch_batch(batch, include_elevation=True, cell_selection=DEFAULT_CELL_SELECTION))
        for batch in self.split_batches(explicit_nearest):
            results.append(
                self.fetch_batch(
                    batch,
                    include_elevation=True,
                    cell_selection=NULL_ELEVATION_CELL_SELECTION,
                )
            )
        for batch in self.split_batches(without_elevation):
            # Without catalog elevation, prefer the geographically nearest grid cell.
            results.append(
                self.fetch_batch(
                    batch,
                    include_elevation=False,
                    cell_selection=NULL_ELEVATION_CELL_SELECTION,
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

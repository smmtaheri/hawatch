from __future__ import annotations

from typing import Protocol


class WeatherProvider(Protocol):
    """Future adapter for Open-Meteo or another provider."""

    def fetch_raw(self, latitude: float, longitude: float, **kwargs) -> dict: ...


class RawWeatherStore(Protocol):
    def save(self, payload: dict, metadata: dict) -> None: ...


class ForecastNormalizer(Protocol):
    def normalize(self, raw: dict, metadata: dict) -> list[dict]: ...


class ForecastRepository(Protocol):
    def upsert_latest(self, records: list[dict]) -> None: ...


class RetentionPolicy(Protocol):
    raw_days: int
    forecast_days: int

    def cleanup(self) -> None: ...


class JobLock(Protocol):
    def acquire(self, name: str, ttl_seconds: int) -> bool: ...

    def release(self, name: str) -> None: ...

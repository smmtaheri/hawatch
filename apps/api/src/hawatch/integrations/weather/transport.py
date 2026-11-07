"""Shared outbound HTTP transport for weather providers."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request
from urllib.parse import parse_qs, urlsplit

from hawatch.integrations.weather.rate_limit import (
    WeatherRateLimiter, quota_retry_delay, request_weight, retry_after_seconds,
)

from hawatch.integrations.weather.proxy_pool import (
    record_proxy_failure,
    record_proxy_success,
    select_weather_proxy,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class JsonResponse:
    status_code: int
    payload: object
    retry_after: float | None = None
    proxy_id: int | None = None


class WeatherHttpTransport:
    """GET JSON with a DB-selected SOCKS proxy and safe retry metadata.

    ``opener`` is kept as a test seam and for compatibility with existing
    provider unit tests.  Runtime calls use requests with PySocks support.
    """

    def __init__(self, *, opener=None, requester=None, rate_limiter=None):
        self._opener = opener
        self._limiter = rate_limiter if rate_limiter is not None else WeatherRateLimiter()
        self._session = None
        self._requests = None
        if requester is not None:
            self._requester = requester
        else:
            # Keep Django schema/admin commands usable in an old running image
            # until the next image rebuild installs the SOCKS dependency.
            import requests

            self._requests = requests
            self._session = requests.Session()
            # A missing active DB proxy means a genuinely direct request, not
            # an accidental HTTP(S)_PROXY inherited from the container.
            self._session.trust_env = False
            self._requester = self._session.get

    def get_json(self, url: str, *, timeout: float, user_agent: str, attempt: int = 1) -> JsonResponse:
        # Acquire before choosing a proxy; changing exits does not bypass quota.
        with self._limiter.request(url, timeout=timeout) as waited:
            started = time.monotonic()
            response = self._get_json(url, timeout=timeout, user_agent=user_agent)
            delay = response.retry_after
            if response.status_code == 429:
                delay = quota_retry_delay(response.payload, delay, retry=attempt - 1)
                self._limiter.cooldown(delay)
            query = parse_qs(urlsplit(url).query)
            log.info("Weather provider HTTP attempt", extra={
                "event": "weather.request_attempt", "provider": urlsplit(url).hostname,
                "model": query.get("models", ["best_match"])[0][:64],
                "point_count": len(query.get("latitude", [""])[0].split(",")),
                "weight": round(request_weight(url), 3), "attempt": attempt,
                "status_code": response.status_code, "proxy_id": response.proxy_id,
                "duration_seconds": round(time.monotonic() - started, 3),
                "quota_wait_seconds": round(waited, 3), "retry_after_seconds": delay,
            })
            return JsonResponse(response.status_code, response.payload, delay, response.proxy_id)

    def _get_json(self, url: str, *, timeout: float, user_agent: str) -> JsonResponse:
        if self._opener is not None:
            return self._get_with_legacy_opener(url, timeout=timeout, user_agent=user_agent)

        if self._requests is None:
            import requests

            self._requests = requests

        selection = select_weather_proxy()
        request_kwargs = {
            "headers": {"User-Agent": user_agent},
            "timeout": timeout,
        }
        if selection is not None:
            request_kwargs["proxies"] = {"http": selection.uri, "https": selection.uri}
        try:
            response = self._requester(url, **request_kwargs)
        except self._requests.RequestException as exc:
            record_proxy_failure(selection, f"transport:{type(exc).__name__}")
            return JsonResponse(0, {"transport_error": type(exc).__name__}, proxy_id=selection.id if selection else None)

        # Any HTTP response proves that the selected network path worked. A
        # provider-level 4xx/5xx is handled by the provider's retry policy and
        # should not falsely mark the proxy as unhealthy.
        record_proxy_success(selection)
        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError):
            payload = {"raw_error": str(getattr(response, "text", ""))[:512]}
        headers = getattr(response, "headers", {}) or {}
        return JsonResponse(int(response.status_code), payload,
                            retry_after_seconds(headers.get("Retry-After")),
                            selection.id if selection else None)

    def _get_with_legacy_opener(self, url: str, *, timeout: float, user_agent: str) -> JsonResponse:
        request = Request(url, headers={"User-Agent": user_agent})
        try:
            response = self._opener(request, timeout=timeout)
            body = response.read().decode("utf-8")
            status = getattr(response, "status", 200)
            close = getattr(response, "close", None)
            if close is not None:
                close()
            headers = getattr(response, "headers", {}) or {}
            return JsonResponse(status, json.loads(body), retry_after_seconds(headers.get("Retry-After")))
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"raw_error": body[:512]}
            return JsonResponse(error.code, parsed, retry_after_seconds((error.headers or {}).get("Retry-After")))
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            return JsonResponse(0, {"transport_error": type(error).__name__})

"""Database-backed, concurrency-safe round-robin weather proxy pool."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from hawatch.common.proxy import request_proxy_uri
from hawatch.modules.forecasts.models import WeatherProxy, WeatherProxyRotation


@dataclass(frozen=True)
class SelectedProxy:
    id: int
    country_code: str
    uri: str


def select_weather_proxy() -> SelectedProxy | None:
    """Select the next active proxy in durable round-robin order.

    A row lock on the cursor makes the sequence stable across Gunicorn,
    scheduler and manual ingest processes.  ``None`` explicitly means that
    the operator has no active proxy and the caller may connect directly.
    """

    with transaction.atomic():
        cursor, _ = (
            WeatherProxyRotation.objects.select_for_update().get_or_create(scope="weather")
        )
        active = list(WeatherProxy.objects.filter(is_active=True).order_by("sort_order", "pk"))
        if not active:
            return None

        previous_id = cursor.last_proxy_id
        previous_index = next(
            (index for index, proxy in enumerate(active) if proxy.pk == previous_id),
            -1,
        )
        selected = active[(previous_index + 1) % len(active)]
        now = timezone.now()
        WeatherProxy.objects.filter(pk=selected.pk).update(
            last_used_at=now,
            updated_at=now,
        )
        cursor.last_proxy_id = selected.pk
        cursor.save(update_fields=["last_proxy", "updated_at"])
        uri = request_proxy_uri(selected.proxy_url)

    return SelectedProxy(id=selected.pk, country_code=selected.country_code, uri=uri)


def record_proxy_failure(selection: SelectedProxy | None, error_code: str) -> None:
    """Store redacted transport health metadata; never persist exception text."""

    if selection is None:
        return
    now = timezone.now()
    WeatherProxy.objects.filter(pk=selection.id).update(
        last_failure_at=now,
        failure_count=F("failure_count") + 1,
        last_error=str(error_code)[:64],
        updated_at=now,
    )


def record_proxy_success(selection: SelectedProxy | None) -> None:
    if selection is None:
        return
    now = timezone.now()
    WeatherProxy.objects.filter(pk=selection.id).update(
        last_success_at=now,
        failure_count=0,
        last_error="",
        updated_at=now,
    )

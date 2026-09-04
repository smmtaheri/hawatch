from __future__ import annotations

import pytest
from django.db import connection

from hawatch.integrations.weather.providers.open_meteo import OpenMeteoProvider, ProviderPoint
from hawatch.integrations.weather.proxy_pool import select_weather_proxy
from hawatch.modules.forecasts.models import WeatherProxy, WeatherProxyRotation


def _proxy(name: str, country: str, order: int) -> WeatherProxy:
    return WeatherProxy.objects.create(
        name=name,
        country_code=country,
        proxy_url=f"socks5://{country.lower()}:secret@192.0.2.{order}:9000",
        sort_order=order,
    )


@pytest.mark.django_db(transaction=True)
def test_proxy_rotation_is_durable_and_skips_inactive_rows():
    first = _proxy("Canada", "CA", 10)
    second = _proxy("United States", "US", 20)

    assert select_weather_proxy().id == first.id
    assert select_weather_proxy().id == second.id
    assert select_weather_proxy().id == first.id

    second.is_active = False
    second.save(update_fields=["is_active", "updated_at"])
    assert select_weather_proxy().id == first.id
    assert WeatherProxyRotation.objects.get(scope="weather").last_proxy_id == first.id


@pytest.mark.django_db(transaction=True)
def test_no_active_proxy_means_direct_request_and_encrypted_storage():
    proxy = _proxy("Canada", "CA", 10)
    proxy.is_active = False
    proxy.save(update_fields=["is_active", "updated_at"])
    assert select_weather_proxy() is None

    with connection.cursor() as cursor:
        cursor.execute("SELECT proxy_url FROM forecasts_weatherproxy WHERE id = %s", [proxy.id])
        stored = cursor.fetchone()[0]
    assert "secret" not in stored
    assert "socks5://" not in stored


@pytest.mark.django_db(transaction=True)
def test_open_meteo_uses_rotating_socks_proxy_and_remote_dns():
    first = _proxy("Canada", "CA", 10)
    second = _proxy("United States", "US", 20)
    calls: list[dict] = []

    class Response:
        status_code = 200
        text = "{}"

        def json(self):
            return []

    def requester(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return Response()

    provider = OpenMeteoProvider(requester=requester, max_retries=0)
    point = ProviderPoint("sample", 35.8843493, 51.4198766, 3955)
    provider.fetch_batch([point], include_elevation=True)
    provider.fetch_batch([point], include_elevation=True)

    assert calls[0]["proxies"]["https"] == "socks5h://ca:secret@192.0.2.10:9000"
    assert calls[1]["proxies"]["https"] == "socks5h://us:secret@192.0.2.20:9000"
    assert WeatherProxy.objects.get(pk=first.id).last_used_at is not None
    assert WeatherProxy.objects.get(pk=second.id).last_used_at is not None


@pytest.mark.django_db(transaction=True)
def test_retry_rotates_to_next_proxy_without_direct_fallback():
    _proxy("Canada", "CA", 10)
    _proxy("United States", "US", 20)
    calls: list[dict] = []

    class Response:
        def __init__(self, status_code):
            self.status_code = status_code
            self.text = "{}"

        def json(self):
            return {"error": "temporary"}

    def requester(url, **kwargs):
        calls.append(kwargs)
        return Response(503 if len(calls) == 1 else 200)

    provider = OpenMeteoProvider(requester=requester, max_retries=1, sleeper=lambda _: None)
    result = provider.fetch_batch(
        [ProviderPoint("sample", 35.8843493, 51.4198766, 3955)],
        include_elevation=True,
    )

    assert result.status_code == 200
    assert calls[0]["proxies"]["https"].startswith("socks5h://ca:")
    assert calls[1]["proxies"]["https"].startswith("socks5h://us:")

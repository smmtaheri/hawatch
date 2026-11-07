"""Real Redis scripts, isolated from every runtime cache and provider."""
import shutil
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import redis

from hawatch.integrations.weather.rate_limit import (
    RELEASE_LUA, WeatherQuotaUnavailable, WeatherRateLimiter,
    quota_retry_delay, request_weight, retry_after_seconds,
)
from hawatch.integrations.weather.transport import WeatherHttpTransport
from hawatch.integrations.weather.providers.open_meteo import OpenMeteoProvider, ProviderPoint


@pytest.fixture(scope="module")
def quota_redis(tmp_path_factory):
    binary = shutil.which("redis-server")
    if not binary:
        pytest.skip("Install redis-server to exercise quota Lua scripts")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    directory = tmp_path_factory.mktemp("weather-quota-redis")
    process = subprocess.Popen([binary, "--bind", "127.0.0.1", "--port", str(port),
                                "--dir", str(directory), "--save", "", "--appendonly", "no"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    client = redis.Redis(host="127.0.0.1", port=port, socket_timeout=2)
    try:
        for _ in range(100):
            try:
                if client.ping():
                    break
            except redis.RedisError:
                time.sleep(.02)
        else:
            pytest.fail("Isolated quota Redis did not start")
        yield client
    finally:
        client.close()
        process.terminate()
        process.wait(timeout=5)


@pytest.fixture
def limiter(settings, quota_redis):
    settings.OPEN_METEO_RATE_LIMIT_ENABLED = True
    settings.OPEN_METEO_RATE_LIMIT_SCOPE = "test-" + uuid4().hex
    settings.OPEN_METEO_REQUEST_INTERVAL_SECONDS = 0
    return WeatherRateLimiter(client=quota_redis)


def now_ms(client):
    sec, usec = client.time()
    return sec * 1000 + usec // 1000


def release(limiter, token):
    limiter._eval(RELEASE_LUA, [limiter.keys[3]], token)


@pytest.mark.parametrize("locations,variables,days,models,expected", [
    (25,14,10,1,35), (100,14,10,1,140), (25,52,10,1,130),
    (2,15,28,2,12), (1,0,1,1,1),
])
def test_weight_scales_with_request_size(locations, variables, days, models, expected):
    url = ("https://api.open-meteo.com/v1/forecast?latitude=" + ",".join(["35"]*locations)
           + "&hourly=" + ",".join(["temperature_2m"]*variables)
           + "&models=" + ",".join(["ecmwf_ifs"]*models) + "&forecast_days=" + str(days))
    assert request_weight(url) == pytest.approx(expected)


def test_retry_after_http_date_and_invalid_values():
    now = datetime(2026,11,7,10,tzinfo=timezone.utc)
    assert retry_after_seconds("Sat, 07 Nov 2026 10:03:00 GMT", now=now) == 180
    assert retry_after_seconds("NaN") is None
    assert retry_after_seconds("garbage") is None
    assert retry_after_seconds("-2") == 0
    assert quota_retry_delay({"retry_after": 0.25}) == 65
    assert quota_retry_delay({}, 400) == 400
    assert quota_retry_delay({"reason":"Hourly API request limit exceeded"}) == 3605
    assert quota_retry_delay({"reason":"Daily API request limit exceeded"}) == 86405


def test_two_independent_clients_cannot_send_concurrently(limiter, quota_redis):
    other = WeatherRateLimiter(client=quota_redis)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda args: args[0].try_reserve(35,args[1],180000),
                                [(limiter,"first"),(other,"second")]))
    assert sum(r[0] for r in results) == 1
    assert next(r for r in results if not r[0])[2] == "inflight"
    for token in ("first","second"):
        release(limiter,token)


def test_spacing_applies_across_instances(limiter, quota_redis):
    limiter.interval_ms = 10000
    assert limiter.try_reserve(35,"first",180000)[0]
    release(limiter,"first")
    other = WeatherRateLimiter(client=quota_redis)
    allowed,wait,reason = other.try_reserve(35,"second",180000)
    assert not allowed and reason == "spacing" and 9 <= wait <= 10


@pytest.mark.parametrize("index,window,name", [(0,60000,"minute"),(1,3600000,"hour"),(2,86400000,"day")])
def test_weighted_rolling_windows_and_expiry(limiter, index, window, name):
    limits = [1000000,1000000,1000000]
    limits[index] = 50000
    limiter.limits = tuple(limits)
    now = now_ms(limiter.client)
    # Inside this window, outside all shorter windows.
    age = window // 2
    limiter.client.zadd(limiter.keys[0], {"history:35000": now-age})
    allowed,wait,reason = limiter.try_reserve(35,"next",180000)
    assert not allowed and reason == name and wait > 0
    limiter.client.zadd(limiter.keys[0], {"history:35000": now-window-10})
    assert limiter.try_reserve(35,"next",180000)[0]
    release(limiter,"next")


def test_cooldown_and_slower_pace_survive_new_provider_instances(limiter, quota_redis):
    limiter.interval_ms = 10000
    limiter.cooldown(65)
    other = WeatherRateLimiter(client=quota_redis)
    allowed,wait,reason = other.try_reserve(35,"blocked",180000)
    assert not allowed and reason == "cooldown" and 64 <= wait <= 65
    assert int(quota_redis.get(limiter.keys[4])) == 20000
    limiter.cooldown(120)
    assert int(quota_redis.get(limiter.keys[4])) == 40000


def test_collection_can_wait_beyond_fifteen_minutes(limiter):
    limiter.client.zadd(limiter.keys[0], {"quota:9000000": now_ms(limiter.client)})
    waits=[]
    def sleep(seconds):
        waits.append(seconds)
        if sum(waits) > 1200:
            limiter.client.delete(limiter.keys[0])
    limiter._sleep=sleep
    with limiter.request("https://api.open-meteo.com/v1/forecast?latitude=35",timeout=60) as waited:
        assert waited > 1200
    assert sum(waits) > 1200


def test_coordinator_failure_never_sends_unmetered_request(settings):
    settings.OPEN_METEO_RATE_LIMIT_ENABLED=True
    class Broken:
        def eval(self,*args):
            raise redis.ConnectionError("credentials-must-not-be-logged")
    limiter=WeatherRateLimiter(client=Broken())
    calls=[]
    transport=WeatherHttpTransport(rate_limiter=limiter,requester=lambda *a,**kw:calls.append(1))
    with pytest.raises(WeatherQuotaUnavailable,match="coordinator unavailable"):
        transport.get_json("https://api.open-meteo.com/v1/forecast",timeout=60,user_agent="test")
    assert not calls


def test_request_lease_released_after_http_failure(limiter):
    with pytest.raises(RuntimeError):
        with limiter.request("https://api.open-meteo.com/v1/forecast",timeout=60):
            assert limiter.client.exists(limiter.keys[3])
            raise RuntimeError("HTTP failed")
    assert not limiter.client.exists(limiter.keys[3])


def test_real_http_header_is_preserved_and_shared(limiter):
    class Response:
        status=429
        headers={"Retry-After":"240"}
        def read(self):return b'{"reason":"Minutely API request limit exceeded"}'
    transport=WeatherHttpTransport(opener=lambda *a,**kw:Response(),rate_limiter=limiter)
    response=transport.get_json("https://api.open-meteo.com/v1/forecast",timeout=60,user_agent="test")
    assert response.retry_after == 240
    other = WeatherRateLimiter(client=limiter.client)
    allowed, wait, reason = other.try_reserve(1, "blocked-after-http-429", 180000)
    assert not allowed and reason == "cooldown" and 239 <= wait <= 240
    assert not limiter.client.exists(limiter.keys[3])


def test_exhausted_429_defers_remaining_batches_without_new_requests():
    calls=[];waits=[]
    class Response:
        status=429
        def read(self):return b'{"reason":"Minutely API request limit exceeded"}'
    def opener(*a,**kw):
        calls.append(1)
        return Response()
    provider=OpenMeteoProvider(batch_size=1,opener=opener,sleeper=waits.append)
    results=provider.fetch_all([ProviderPoint(str(i),35,51,100) for i in range(3)])
    assert len(calls)==4 and waits==[65,120,180]
    assert [r.attempts for r in results]==[4,0,0]
    assert provider.stop_reason=="provider_rate_limited"


def test_legacy_large_batch_setting_is_safely_capped(settings):
    settings.OPEN_METEO_BATCH_SIZE=100
    assert OpenMeteoProvider().batch_size==25

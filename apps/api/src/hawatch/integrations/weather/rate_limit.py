"""Shared, weighted outbound quota. Waiting never holds a DB transaction.

Redis TIME and atomic reservations coordinate scheduler/manual/API processes.
Quotas are application-wide: changing the model or proxy does not reset them.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from django.conf import settings

log = logging.getLogger(__name__)


class WeatherQuotaUnavailable(RuntimeError):
    """No request may bypass a failed shared quota coordinator."""


def request_weight(url: str) -> float:
    """Open-Meteo call equivalents; count coordinates, not HTTP envelopes."""
    query = parse_qs(urlsplit(url).query)
    def count(key):
        return sum(bool(value) for item in query.get(key, []) for value in item.split(","))

    locations = max(1, count("latitude"))
    variables = sum(count(key) for key in ("hourly", "daily", "current", "minutely_15"))
    models = max(1, count("models"))
    try:
        days = float(query.get("forecast_days", [7])[0]) + float(query.get("past_days", [0])[0])
    except (ValueError, TypeError):
        days = 14
    if not math.isfinite(days) or days < 0:
        raise ValueError("Invalid weather forecast window")
    return locations * models * max(1, variables / 10) * max(1, days / 14)


def retry_after_seconds(value, *, now: datetime | None = None) -> float | None:
    """Accept both Retry-After seconds and HTTP-date, never NaN/negative."""
    if value is None:
        return None
    try:
        seconds = float(value)
    except (ValueError, TypeError):
        try:
            stamp = parsedate_to_datetime(str(value))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            seconds = (stamp - (now or datetime.now(timezone.utc))).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return None
    return max(0.0, seconds) if math.isfinite(seconds) else None


def quota_retry_delay(payload, header=None, *, retry: int = 0) -> float:
    reason = str(payload.get("reason", "")).lower() if isinstance(payload, dict) else ""
    floor = 86405 if "daily" in reason else 3605 if "hourly" in reason else (65, 120, 180)[min(retry, 2)]
    candidates = [retry_after_seconds(header)]
    if isinstance(payload, dict):
        candidates += [retry_after_seconds(payload.get(k)) for k in ("retry_after", "Retry-After")]
    return max([float(floor), *(v for v in candidates if v is not None)])


# Members contain milli-call weights so sums/rounding are deterministic. At the
# default budget there are ~260 full batches/day, keeping the scan very small.
RESERVE_LUA = """
local t = redis.call('TIME')
local now = tonumber(t[1])*1000 + math.floor(tonumber(t[2])/1000)
local weight = tonumber(ARGV[1])
local wait = 0
local cause = 'spacing'
local function delay(until_at, why)
  if until_at-now > wait then wait=until_at-now; cause=why end
end
delay(tonumber(redis.call('GET', KEYS[2]) or '0'), 'spacing')
delay(tonumber(redis.call('GET', KEYS[3]) or '0'), 'cooldown')
if redis.call('EXISTS', KEYS[4]) == 1 then
  delay(now+math.min(1000, math.max(1,redis.call('PTTL',KEYS[4]))), 'inflight')
end
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now-86400000)
local windows = {60000,3600000,86400000}
local names = {'minute','hour','day'}
for i,window in ipairs(windows) do
  local limit = tonumber(ARGV[i+4])
  if weight > limit then return {-1,0,'oversized'} end
  local rows = redis.call('ZRANGEBYSCORE', KEYS[1], '('..(now-window), '+inf', 'WITHSCORES')
  local total = weight
  for j=1,#rows,2 do total=total+tonumber(string.match(rows[j],':(%d+)$')) end
  if total > limit then
    for j=1,#rows,2 do
      total=total-tonumber(string.match(rows[j],':(%d+)$'))
      if total <= limit then delay(tonumber(rows[j+1])+window+1,names[i]); break end
    end
  end
end
if wait > 0 then return {0,math.ceil(wait),cause} end
local interval = math.max(tonumber(ARGV[3]),tonumber(redis.call('GET',KEYS[5]) or '0'))
redis.call('SET',KEYS[4],ARGV[2],'PX',ARGV[4])
redis.call('ZADD',KEYS[1],now,ARGV[2]..':'..ARGV[1])
redis.call('PEXPIRE',KEYS[1],90000000)
redis.call('SET',KEYS[2],now+interval,'PX',math.max(1,interval))
return {1,now,'reserved'}
"""

COOLDOWN_LUA = """
local t=redis.call('TIME')
local now=tonumber(t[1])*1000+math.floor(tonumber(t[2])/1000)
local until_at=math.max(now+tonumber(ARGV[1]),tonumber(redis.call('GET',KEYS[1]) or '0'))
redis.call('SET',KEYS[1],until_at,'PX',math.max(1,until_at-now))
local strikes=redis.call('INCR',KEYS[3])
redis.call('EXPIRE',KEYS[3],3600)
redis.call('SET',KEYS[2],math.min(60000,tonumber(ARGV[2])*2^math.min(strikes,6)),'EX',3600)
return until_at
"""

RENEW_LUA = """
if redis.call('GET',KEYS[1]) == ARGV[1] then
  return redis.call('PEXPIRE',KEYS[1],ARGV[2])
end
return 0
"""
RELEASE_LUA = """
if redis.call('GET',KEYS[1]) == ARGV[1] then return redis.call('DEL',KEYS[1]) end
return 0
"""


class WeatherRateLimiter:
    def __init__(self, *, client=None, sleeper=None):
        self.enabled = settings.OPEN_METEO_RATE_LIMIT_ENABLED
        self._client = client
        self._sleep = sleeper or time.sleep
        self.interval_ms = int(settings.OPEN_METEO_REQUEST_INTERVAL_SECONDS * 1000)
        self.limits = tuple(int(v * 1000) for v in (
            settings.OPEN_METEO_CALLS_PER_MINUTE,
            settings.OPEN_METEO_CALLS_PER_HOUR,
            settings.OPEN_METEO_CALLS_PER_DAY,
        ))
        if self.interval_ms < 0 or min(self.limits) <= 0:
            raise ValueError("Weather quota limits must be positive")
        prefix = "hawatch:weather-quota:{" + settings.OPEN_METEO_RATE_LIMIT_SCOPE + "}:v1:"
        self.keys = [prefix + key for key in ("events", "next", "cooldown", "lease", "adaptive", "strikes")]

    @property
    def client(self):
        if self._client is None:
            import redis
            url = settings.OPEN_METEO_RATE_LIMIT_REDIS_URL
            if not url:
                raise WeatherQuotaUnavailable("Weather quota Redis is not configured")
            self._client = redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        return self._client

    def _eval(self, script, keys, *args):
        try:
            return self.client.eval(script, len(keys), *keys, *args)
        except WeatherQuotaUnavailable:
            raise
        except Exception as exc:
            # Never include Redis URLs/passwords in exceptions or logs.
            raise WeatherQuotaUnavailable("Weather quota coordinator unavailable") from exc

    def try_reserve(self, weight, token, lease_ms):
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError("Invalid weather request weight")
        result = self._eval(RESERVE_LUA, self.keys[:5], math.ceil(weight * 1000), token,
                            self.interval_ms, lease_ms, *self.limits)
        cause = result[2].decode() if isinstance(result[2], bytes) else result[2]
        if result[0] == -1:
            raise WeatherQuotaUnavailable("Weather batch exceeds configured quota; reduce batch size")
        return bool(result[0]), result[1] / 1000, cause

    def cooldown(self, seconds):
        if self.enabled:
            self._eval(COOLDOWN_LUA, [self.keys[2], self.keys[4], self.keys[5]],
                       math.ceil(seconds * 1000), self.interval_ms)

    @contextmanager
    def request(self, url, *, timeout):
        if not self.enabled:
            yield 0.0
            return
        weight = request_weight(url)
        token = uuid4().hex
        lease_ms = max(180000, math.ceil((timeout * 2 + 60) * 1000))
        waited = 0.0
        while True:
            allowed, seconds, cause = self.try_reserve(weight, token, lease_ms)
            if allowed:
                break
            if seconds >= 1 and cause != "inflight":
                log.info("Weather request waiting for shared quota", extra={
                    "event": "weather.quota_wait", "reason": cause,
                    "wait_seconds": round(seconds, 3), "weight": weight,
                })
            pause = min(30.0, seconds)
            self._sleep(pause)
            waited += pause
        stop = threading.Event()
        lost = threading.Event()

        def renew():
            while not stop.wait(15):
                try:
                    if not self._eval(RENEW_LUA, [self.keys[3]], token, lease_ms):
                        lost.set()
                        return
                except WeatherQuotaUnavailable:
                    lost.set()
                    return

        heartbeat = threading.Thread(target=renew, name="weather-quota-lease", daemon=True)
        heartbeat.start()
        try:
            yield waited
            if lost.is_set():
                raise WeatherQuotaUnavailable("Weather quota request lease lost")
        finally:
            stop.set()
            heartbeat.join(timeout=3)
            self._eval(RELEASE_LUA, [self.keys[3]], token)

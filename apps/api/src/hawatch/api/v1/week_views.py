from datetime import timedelta
from hashlib import sha256
import json
import logging
import time
import zlib
from django.core.cache import cache
from django.db import DatabaseError
from django.http import HttpResponse
from django.utils.dateparse import parse_datetime
from django.utils.http import parse_etags
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import NotFound
from hawatch.common.time import now_tehran, localize_dt
from hawatch.modules.forecasts.models import LastGoodWeekForecast
from .week_bundles import build_week, has_usable_week_data
from .week_cache import revision
from .week_interest import payload_ttl, touch_page

WEEK_CACHE_SCHEMA = "week-12"
LAST_GOOD_CACHE_SECONDS = 30 * 24 * 60 * 60
log = logging.getLogger(__name__)


def _last_good_key(kind, slug):
    return f"week-last-good:v1:{kind}:{slug}"


def _decode_last_good(stored, *, expected_catalog_signature=None):
    if not stored:
        return None
    try:
        body = zlib.decompress(bytes(stored[0]))
        digest = sha256(body).hexdigest()
        if stored[1] != digest:
            return None
        payload = json.loads(body)
        if payload.get("schema_version") != "week-2" or not has_usable_week_data(payload):
            return None
        if expected_catalog_signature and payload.get("catalog_signature") != expected_catalog_signature:
            return None
        return body, f'"{digest}"'
    except (TypeError, ValueError, zlib.error, json.JSONDecodeError):
        return None


def _load_last_good(kind, slug, *, expected_catalog_signature=None):
    key = _last_good_key(kind, slug)
    try:
        cached = _decode_last_good(cache.get(key), expected_catalog_signature=expected_catalog_signature)
        if cached:
            return cached
    except Exception:
        pass
    try:
        row = LastGoodWeekForecast.objects.filter(kind=kind, slug=slug).only(
            "schema_version", "payload", "payload_sha256", "catalog_signature"
        ).first()
    except DatabaseError:
        log.exception("Could not read durable last-good week forecast for %s:%s", kind, slug)
        return None
    if row is None or row.schema_version != "week-2":
        return None
    decoded = _decode_last_good((row.payload, row.payload_sha256), expected_catalog_signature=expected_catalog_signature)
    if decoded:
        try:
            cache.set(key, (zlib.compress(decoded[0], level=3), row.payload_sha256), LAST_GOOD_CACHE_SECONDS)
        except Exception:
            pass
    return decoded


def _store_last_good(kind, slug, body, payload):
    attribution = payload.get("attribution") or {}
    updated_at = attribution.get("updated_at")
    if not updated_at or not has_usable_week_data(payload):
        return
    updated_at = parse_datetime(updated_at)
    if updated_at is None:
        return
    digest = sha256(body).hexdigest()
    compressed = zlib.compress(body, level=6)
    source_label = str(attribution.get("source") or "")[:160]
    try:
        row = LastGoodWeekForecast.objects.filter(kind=kind, slug=slug).only("id", "payload_sha256").first()
        if row is None:
            LastGoodWeekForecast.objects.create(
                kind=kind,
                slug=slug,
                schema_version="week-2",
                payload=compressed,
                payload_sha256=digest,
                catalog_signature=payload["catalog_signature"],
                updated_at=updated_at,
                source_label=source_label,
            )
        elif row.payload_sha256 != digest:
            LastGoodWeekForecast.objects.filter(pk=row.pk).update(
                schema_version="week-2",
                payload=compressed,
                payload_sha256=digest,
                catalog_signature=payload["catalog_signature"],
                updated_at=updated_at,
                source_label=source_label,
            )
    except DatabaseError:
        # Redis and the live response remain useful if the durable mirror is
        # temporarily unavailable; do not fail a good forecast for its cache.
        log.exception("Could not persist last-good week forecast for %s:%s", kind, slug)
    try:
        cache.set(_last_good_key(kind, slug), (zlib.compress(body, level=3), digest), LAST_GOOD_CACHE_SECONDS)
    except Exception:
        pass

def cached_week(kind, slug, today):
    # Bump the payload schema when serialization changes, independently of UI releases.
    key = f"{WEEK_CACHE_SCHEMA}:{revision()}:{kind}:{slug}:{today}"
    try:
        stored = cache.get(key)
        if stored: return (zlib.decompress(stored[0]), stored[1]), "HIT"
        owner = cache.add(key+":building", True, 60)
        if not owner:
            for _ in range(100):
                time.sleep(.05)
                stored = cache.get(key)
                if stored: return (zlib.decompress(stored[0]), stored[1]), "HIT"
    except Exception:
        owner = False
    try:
        try:
            payload = build_week(kind, slug, today)
        except NotFound:
            # An unknown or inactive URL must stay a real 404, not inherit a
            # previous bundle belonging to a deleted catalog entry.
            raise
        except Exception:
            log.exception("Live week build failed for %s:%s; trying last-good forecast", kind, slug)
            fallback = _load_last_good(kind, slug)
            if fallback:
                try:
                    cache.set(key, (zlib.compress(fallback[0], level=3), fallback[1]), 60)
                except Exception:
                    pass
                return fallback, "LAST-GOOD"
            raise

        if not has_usable_week_data(payload):
            fallback = _load_last_good(
                kind, slug, expected_catalog_signature=payload.get("catalog_signature")
            )
            if fallback:
                # Retry the live builder soon, but keep the last complete
                # response on screen instead of caching an empty week.
                try:
                    cache.set(key, (zlib.compress(fallback[0], level=3), fallback[1]), 60)
                except Exception:
                    pass
                return fallback, "LAST-GOOD"

        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        stored = (body, '"'+sha256(body).hexdigest()+'"')
        if has_usable_week_data(payload):
            _store_last_good(kind, slug, body, payload)
        until_midnight = max(1, int((localize_dt(today+timedelta(days=1),0)-now_tehran()).total_seconds()))
        try:
            cache.set(key, (zlib.compress(body, level=3), stored[1]), min(until_midnight, payload_ttl()) if payload["last_generated_at"] else 120)
        except Exception: pass
        return stored, "MISS"
    finally:
        if owner:
            try: cache.delete(key+":building")
            except Exception: pass

@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def week_forecast(request, slug, kind):
    local = now_tehran()
    # Only this week's anonymous forecast is shared. Selection stays in the UI.
    if request.query_params:
        from rest_framework.exceptions import ValidationError
        raise ValidationError("API هفته پارامتر انتخاب برنامه ندارد")
    (body, etag), status = cached_week(kind, slug, local.date())
    max_age = max(0,min(120,int((localize_dt(local.date()+timedelta(days=1),0)-local).total_seconds())))
    # GET uses weak comparison: gzip/CDNs may prefix our strong ETag with W/.
    candidates = parse_etags(request.headers.get("If-None-Match", ""))
    unchanged = "*" in candidates or any(tag.removeprefix("W/") == etag for tag in candidates)
    response = HttpResponse(status=304) if unchanged else HttpResponse(body,content_type="application/json; charset=utf-8")
    response["ETag"] = etag
    response["Cache-Control"] = f"private, max-age={max_age}, must-revalidate"
    response["CDN-Cache-Control"] = "no-store"
    response["Surrogate-Control"] = "no-store"
    response["Vary"] = "Accept-Encoding"
    response["X-Hawatch-Cache"] = status
    return response


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def week_visit(request, slug, kind):
    # Separate from GET/poll/warming so only page openings renew the 48h lease.
    from .week_bundles import get_point, get_route
    (get_point if kind == "point" else get_route)(slug)
    touch_page(kind, slug)
    response = HttpResponse(status=204)
    response["Cache-Control"] = "no-store"
    return response

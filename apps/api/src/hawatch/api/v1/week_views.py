from datetime import timedelta
from hashlib import sha256
import json
import time
import zlib
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.http import parse_etags
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import NotFound
from hawatch.common.time import now_tehran, localize_dt
from .week_bundles import build_week
from .week_cache import revision
from .week_interest import payload_ttl, touch_page

WEEK_CACHE_SCHEMA = "week-4"

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
        payload = build_week(kind, slug, today)
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        stored = (body, '"'+sha256(body).hexdigest()+'"')
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

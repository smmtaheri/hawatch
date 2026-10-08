from datetime import timedelta
from hashlib import sha256
import json
import time
from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import NotFound
from hawatch.common.time import now_tehran, localize_dt
from .week_bundles import build_week
from .week_cache import revision

def cached_week(kind, slug, today):
    key = f"week-1:{revision()}:{kind}:{slug}:{today}"
    try:
        stored = cache.get(key)
        if stored: return stored, "HIT"
        owner = cache.add(key+":building", True, 60)
        if not owner:
            for _ in range(100):
                time.sleep(.05)
                stored = cache.get(key)
                if stored: return stored, "HIT"
    except Exception:
        owner = False
    try:
        payload = build_week(kind, slug, today)
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        stored = (body, '"'+sha256(body).hexdigest()+'"')
        until_midnight = max(1, int((localize_dt(today+timedelta(days=1),0)-now_tehran()).total_seconds()))
        try:
            cache.set(key, stored, min(until_midnight, 86400) if payload["last_generated_at"] else 120)
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
    response = HttpResponse(status=304) if etag in request.headers.get("If-None-Match", "").split(", ") else HttpResponse(body,content_type="application/json; charset=utf-8")
    response["ETag"] = etag
    response["Cache-Control"] = f"public, max-age={max_age}, s-maxage={max_age}, must-revalidate"
    response["Vary"] = "Accept-Encoding"
    response["X-Hawatch-Cache"] = status
    return response

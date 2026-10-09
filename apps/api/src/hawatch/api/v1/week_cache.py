"""Versioned shared payload cache. Only anonymous, public data enters this cache."""
import logging
from uuid import uuid4
from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_save, post_delete

log = logging.getLogger(__name__)
REVISION_KEY = "forecast-week:revision:v1"

def revision():
    try:
        value = cache.get(REVISION_KEY)
        if value is None:
            value = uuid4().hex
            cache.add(REVISION_KEY, value, None)
            value = cache.get(REVISION_KEY) or value
        return value
    except Exception:
        log.warning("Week cache unavailable; using database fallback")
        return "uncached"

def invalidate_week_cache(**kwargs):
    def change():
        try:
            cache.set(REVISION_KEY, uuid4().hex, None)
        except Exception:
            log.warning("Week cache invalidation failed; Redis unavailable")
    transaction.on_commit(change)

def register_signals():
    for sender in ("forecasts.WeatherPoint", "routes.Route", "routes.RoutePoint"):
        post_save.connect(invalidate_week_cache, sender=sender, dispatch_uid=f"week-save-{sender}")
        post_delete.connect(invalidate_week_cache, sender=sender, dispatch_uid=f"week-delete-{sender}")

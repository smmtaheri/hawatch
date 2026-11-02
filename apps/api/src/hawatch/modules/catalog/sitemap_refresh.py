"""Redis is an optional refresh hint, never the durable sitemap store."""
import logging
from uuid import uuid4

from django.core.cache import cache
from django.db import transaction

log = logging.getLogger("hawatch.sitemap")
DIRTY_KEY = "sitemap:dirty:v1"


def request_sitemap_refresh():
    def mark():
        try:
            cache.set(DIRTY_KEY, uuid4().hex, None)
        except Exception:
            log.warning("Sitemap Redis hint unavailable; periodic generation remains enabled")
    transaction.on_commit(mark)


def refresh_marker():
    try:
        return cache.get(DIRTY_KEY)
    except Exception:
        return None

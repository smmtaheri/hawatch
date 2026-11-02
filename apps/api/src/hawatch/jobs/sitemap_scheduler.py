"""An independent publisher; retention and weather schedules are unchanged."""
import logging
import time

from django.db import close_old_connections, connection

from hawatch.modules.catalog.sitemap import publish_sitemap
from hawatch.modules.catalog.sitemap_refresh import refresh_marker

log = logging.getLogger("hawatch.sitemap")


class SitemapScheduler:
    def __init__(self, *, interval=300, retry_seconds=30):
        self.interval = interval
        self.retry_seconds = retry_seconds
        self.last_attempt = float("-inf")
        self.last_success = float("-inf")
        self.last_marker = None
        self.failed = False

    def tick(self, now=None):
        now = time.monotonic() if now is None else now
        marker = refresh_marker()
        if now - self.last_attempt < self.retry_seconds:
            return
        if not (self.failed or now - self.last_success >= self.interval or marker != self.last_marker):
            return
        self.last_attempt = now
        try:
            if not connection.in_atomic_block:
                close_old_connections()
            result = publish_sitemap()
            if result["status"] == "busy":
                return
            self.last_success = now
            # A change committed DURING this build stays pending for next tick.
            self.last_marker = marker
            self.failed = False
            return result
        except Exception:
            self.failed = True
            log.exception("Sitemap refresh failed; retaining last published XML")
        finally:
            if not connection.in_atomic_block:
                close_old_connections()

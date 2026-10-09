import logging
from django.core.management.base import BaseCommand
from hawatch.common.time import now_tehran
from hawatch.api.v1.week_views import cached_week
from hawatch.api.v1.week_interest import warm_targets

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Warm fixed 100 destinations, their first routes and pages visited in the last 48h"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, limit, **options):
        from hawatch.modules.routes.models import SharedRoutePlan
        SharedRoutePlan.objects.filter(expires_at__lte=now_tehran()).delete()
        today = now_tehran().date()
        count = 0
        for kind, slug in warm_targets(max(0, min(limit, 100))):
            try:
                cached_week(kind, slug, today)
                count += 1
            except Exception:
                # A removed or incomplete page must not prevent all other warming.
                log.exception("Week cache warming failed: %s/%s", kind, slug)
        self.stdout.write(f"Week cache warmed: {count} pages")

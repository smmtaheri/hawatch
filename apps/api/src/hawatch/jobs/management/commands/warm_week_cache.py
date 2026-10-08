from django.core.management.base import BaseCommand
from hawatch.common.time import now_tehran
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route
from hawatch.api.v1.week_views import cached_week

class Command(BaseCommand):
    help = "Prepare a bounded set of public week payloads after ingest"
    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
    def handle(self, limit, **options):
        from hawatch.modules.routes.models import SharedRoutePlan
        SharedRoutePlan.objects.filter(expires_at__lte=now_tehran()).delete()
        today = now_tehran().date()
        for kind, rows in (("point", WeatherPoint.objects.filter(is_active=True).order_by("-is_popular", "popular_order", "slug")), ("route", Route.objects.filter(is_active=True).order_by("-featured", "sort_order"))):
            for slug in rows.values_list("slug",flat=True)[:max(0,min(limit,100))]:
                cached_week(kind,slug,today)
        self.stdout.write("Week cache warmed")

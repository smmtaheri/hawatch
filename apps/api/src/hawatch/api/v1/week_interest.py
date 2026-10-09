"""Warm fixed destinations and recently opened pages after each ingestion."""
import json
import os
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db.models.functions import Greatest
from django.utils import timezone
from hawatch.common.time import now_tehran
from hawatch.jobs.ingest_scheduler import parse_schedule, next_scheduled_run
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route, WeekCacheInterest


def fixed_points():
    return json.loads((Path(settings.BASE_DIR) / "fixtures/week_cache_points.json").read_text())["points"]


def touch_page(kind, slug):
    expires = timezone.now() + timedelta(hours=48)
    row, created = WeekCacheInterest.objects.get_or_create(kind=kind, slug=slug, defaults={"expires_at": expires})
    if not created:
        # Concurrent earlier visits must never shorten a later visit's deadline.
        WeekCacheInterest.objects.filter(pk=row.pk).update(expires_at=Greatest("expires_at", expires))


def warm_targets(limit=100):
    now = timezone.now()
    WeekCacheInterest.objects.filter(expires_at__lte=now).delete()
    selected = fixed_points()[:limit]
    active = set(WeatherPoint.objects.filter(slug__in=selected, is_active=True, seo_indexable=True).values_list("slug", flat=True))
    targets = [("point", slug) for slug in selected if slug in active]
    # Same first route and ordering as the destination page, including point-only destinations.
    first = {}
    for point_slug, route_slug in Route.objects.filter(is_active=True, points__weather_point__slug__in=active).order_by("sort_order", "slug").values_list("points__weather_point__slug", "slug"):
        first.setdefault(point_slug, route_slug)
    targets += [("route", first[slug]) for slug in selected if slug in first]
    targets += list(WeekCacheInterest.objects.filter(expires_at__gt=now).order_by("kind", "slug").values_list("kind", "slug"))
    return list(dict.fromkeys(targets))


def payload_ttl():
    now = now_tehran()
    zone = ZoneInfo(os.getenv("HAWATCH_TIMEZONE", "Asia/Tehran"))
    next_run = next_scheduled_run(now, parse_schedule(os.getenv("HAWATCH_INGEST_SCHEDULE")), zone)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((min(next_run, midnight) - now).total_seconds()))

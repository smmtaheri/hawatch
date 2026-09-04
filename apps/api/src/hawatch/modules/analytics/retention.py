from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import MonthlyPageViewAggregate, PageViewEvent


RAW_RETENTION_DAYS = 30
ANALYTICS_RETENTION_LOCK_KEY = 0x4841574154  # HAWAT


def _local_month_expression():
    return TruncMonth(
        "occurred_at",
        tzinfo=ZoneInfo(getattr(settings, "TIME_ZONE", "Asia/Tehran")),
    )


def aggregate_and_cleanup_page_views(*, dry_run: bool = False) -> dict[str, int | str | bool]:
    """Aggregate and delete raw events older than 30 days.

    The transaction/advisory lock makes retries and overlapping maintenance
    processes safe. Unique visitors are counted per deleted batch/month and are
    therefore intentionally approximate once monthly rows are combined.
    """

    cutoff = timezone.now() - timedelta(days=RAW_RETENTION_DAYS)
    expired = PageViewEvent.objects.filter(occurred_at__lt=cutoff)
    grouped = expired.annotate(month=_local_month_expression()).values(
        "page_type", "page_slug", "month"
    ).annotate(
        page_views=Count("id"),
        unique_visitors=Count("visitor_hash", distinct=True),
    )
    groups = list(grouped)
    result: dict[str, int | str | bool] = {
        "dry_run": dry_run,
        "cutoff": cutoff.isoformat(),
        "aggregate_groups": len(groups),
        "aggregate_page_views": sum(int(item["page_views"]) for item in groups),
        "aggregate_unique_visitors": sum(int(item["unique_visitors"]) for item in groups),
        "deleted_events": expired.count(),
    }
    if dry_run or not groups:
        return result

    with transaction.atomic():
        # PostgreSQL advisory transaction lock serializes retries from multiple
        # maintenance containers without retaining any lock row in the schema.
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [ANALYTICS_RETENTION_LOCK_KEY])
        expired = PageViewEvent.objects.filter(occurred_at__lt=cutoff)
        groups = list(
            expired.annotate(month=_local_month_expression())
            .values("page_type", "page_slug", "month")
            .annotate(page_views=Count("id"), unique_visitors=Count("visitor_hash", distinct=True))
        )
        for item in groups:
            month = item["month"].date() if hasattr(item["month"], "date") else item["month"]
            aggregate, _ = MonthlyPageViewAggregate.objects.get_or_create(
                page_type=item["page_type"],
                page_slug=item["page_slug"],
                month_start=month,
                defaults={"page_views": 0, "unique_visitors": 0},
            )
            aggregate.page_views += int(item["page_views"])
            aggregate.unique_visitors += int(item["unique_visitors"])
            aggregate.save(update_fields=["page_views", "unique_visitors"])
        result["deleted_events"] = expired.delete()[0]
        result["aggregate_groups"] = len(groups)
        result["aggregate_page_views"] = sum(int(item["page_views"]) for item in groups)
        result["aggregate_unique_visitors"] = sum(int(item["unique_visitors"]) for item in groups)
    return result

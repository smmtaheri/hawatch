from django.db import models
from django.utils import timezone


class PageViewEvent(models.Model):
    class PageType(models.TextChoices):
        POINT = "point", "Point"
        ROUTE = "route", "Route"

    page_type = models.CharField(max_length=8, choices=PageType.choices)
    page_slug = models.SlugField(max_length=96)
    # HMAC digest of a first-party random visitor token. The raw token is
    # never sent to or persisted by the API.
    visitor_hash = models.CharField(max_length=64)
    # Generated once per SPA history entry so retries are idempotent.
    navigation_id = models.CharField(max_length=64)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["page_type", "page_slug", "visitor_hash", "navigation_id"],
                name="uniq_analytics_navigation",
            )
        ]
        indexes = [
            models.Index(
                fields=["page_type", "page_slug", "occurred_at"],
                name="analytics_page_period_idx",
            ),
            models.Index(fields=["visitor_hash", "occurred_at"], name="analytics_visitor_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.page_type}:{self.page_slug}"


class MonthlyPageViewAggregate(models.Model):
    """Monthly counters retained after raw page-view events expire."""

    page_type = models.CharField(max_length=8, choices=PageViewEvent.PageType.choices)
    page_slug = models.SlugField(max_length=96)
    month_start = models.DateField()
    page_views = models.PositiveBigIntegerField(default=0)
    # This is intentionally a monthly distinct count. Summing months is an
    # approximation because a visitor can appear in more than one month.
    unique_visitors = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["page_type", "page_slug", "month_start"],
                name="uniq_analytics_monthly_page",
            )
        ]
        indexes = [
            models.Index(fields=["month_start", "page_type", "page_slug"], name="analytics_month_page_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.month_start}:{self.page_type}:{self.page_slug}"

from django.db import models
from django.utils import timezone


class VisitSession(models.Model):
    visitor_hash = models.CharField(max_length=64)
    session_hash = models.CharField(max_length=64)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    source = models.CharField(max_length=24, default="unknown", db_index=True)
    source_evidence = models.CharField(max_length=12, default="none")
    utm_source = models.CharField(max_length=100, blank=True)
    medium = models.CharField(max_length=100, blank=True)
    campaign = models.CharField(max_length=100, blank=True)
    referrer_host = models.CharField(max_length=200, blank=True)
    landing_path = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["visitor_hash", "session_hash"], name="uniq_analytics_session"
            )
        ]
        indexes = [
            models.Index(
                fields=["source", "started_at"], name="analytics_source_time_idx"
            )
        ]


class AnalyticsCoverage(models.Model):
    # Singleton, initialized during migration; never guess historical attribution.
    detailed_since = models.DateTimeField()
    attribution_since = models.DateTimeField()


class PageViewEvent(models.Model):
    class PageType(models.TextChoices):
        POINT = "point", "Point"
        ROUTE = "route", "Route"

    page_type = models.CharField(max_length=8, choices=PageType.choices)
    page_slug = models.SlugField(max_length=96)
    # HMAC digest of a first-party random visitor token. The API receives
    # the anonymous token but never persists its raw value.
    visitor_hash = models.CharField(max_length=64)
    # Stable for retries/effects of one navigation occurrence, including POP.
    navigation_id = models.CharField(max_length=64)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    session = models.ForeignKey(
        VisitSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    previous_path = models.CharField(max_length=200, blank=True)
    navigation_source = models.CharField(max_length=24, default="unknown")

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
            models.Index(
                fields=["visitor_hash", "occurred_at"],
                name="analytics_visitor_time_idx",
            ),
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
            models.Index(
                fields=["month_start", "page_type", "page_slug"],
                name="analytics_month_page_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.month_start}:{self.page_type}:{self.page_slug}"

from datetime import timedelta
from io import StringIO
import json

import pytest
from django.core.management import call_command
from django.utils import timezone

from hawatch.modules.analytics.models import MonthlyPageViewAggregate, PageViewEvent
from hawatch.modules.analytics.retention import aggregate_and_cleanup_page_views


def _event(*, page_type="point", slug="tochal", visitor_hash, navigation_id, occurred_at):
    return PageViewEvent.objects.create(
        page_type=page_type,
        page_slug=slug,
        visitor_hash=visitor_hash,
        navigation_id=navigation_id,
        occurred_at=occurred_at,
    )


@pytest.mark.django_db
def test_analytics_retention_dry_run_then_aggregate_and_delete_is_idempotent():
    old = timezone.now() - timedelta(days=31)
    recent = timezone.now() - timedelta(days=2)
    _event(visitor_hash="a" * 64, navigation_id="old-navigation-0001", occurred_at=old)
    _event(visitor_hash="b" * 64, navigation_id="old-navigation-0002", occurred_at=old)
    _event(visitor_hash="a" * 64, navigation_id="recent-navigation-01", occurred_at=recent)

    preview = aggregate_and_cleanup_page_views(dry_run=True)
    assert preview["aggregate_groups"] == 1
    assert preview["aggregate_page_views"] == 2
    assert preview["deleted_events"] == 2
    assert PageViewEvent.objects.count() == 3
    assert not MonthlyPageViewAggregate.objects.exists()

    applied = aggregate_and_cleanup_page_views()
    assert applied["deleted_events"] == 2
    assert PageViewEvent.objects.count() == 1
    aggregate = MonthlyPageViewAggregate.objects.get(page_slug="tochal")
    assert aggregate.page_views == 2
    assert aggregate.unique_visitors == 2

    repeated = aggregate_and_cleanup_page_views()
    assert repeated["aggregate_groups"] == 0
    assert repeated["deleted_events"] == 0
    assert MonthlyPageViewAggregate.objects.get(pk=aggregate.pk).page_views == 2


@pytest.mark.django_db
def test_analytics_retention_catches_up_later_events_in_same_month():
    old = timezone.now() - timedelta(days=31)
    _event(visitor_hash="c" * 64, navigation_id="catchup-navigation-01", occurred_at=old)
    aggregate_and_cleanup_page_views()

    _event(visitor_hash="c" * 64, navigation_id="catchup-navigation-02", occurred_at=old)
    result = aggregate_and_cleanup_page_views()

    assert result["deleted_events"] == 1
    aggregate = MonthlyPageViewAggregate.objects.get(page_slug="tochal")
    assert aggregate.page_views == 2
    # Repeated monthly distinct visitors are intentionally approximate.
    assert aggregate.unique_visitors == 2


@pytest.mark.django_db
def test_analytics_retention_management_command_dry_run_reports_work():
    _event(
        visitor_hash="e" * 64,
        navigation_id="command-navigation-01",
        occurred_at=timezone.now() - timedelta(days=31),
    )
    output = StringIO()

    call_command("cleanup_analytics_retention", "--dry-run", stdout=output)

    result = json.loads(output.getvalue())
    assert result["dry_run"] is True
    assert result["aggregate_groups"] == 1
    assert result["deleted_events"] == 1

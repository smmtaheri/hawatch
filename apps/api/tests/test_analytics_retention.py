from datetime import timedelta
from io import StringIO
import json
import pytest
from django.core.management import call_command
from django.utils import timezone
from hawatch.modules.analytics.models import MonthlyPageViewAggregate, PageViewEvent
from hawatch.modules.analytics.retention import aggregate_and_cleanup_page_views


@pytest.mark.django_db
def test_exact_history_is_preserved_for_arbitrary_windows_and_repeated_maintenance():
    PageViewEvent.objects.create(
        page_type="point",
        page_slug="tochal",
        visitor_hash="a" * 64,
        navigation_id="old-navigation-0001",
        occurred_at=timezone.now() - timedelta(days=400),
    )
    old = MonthlyPageViewAggregate.objects.create(
        page_type="point",
        page_slug="tochal",
        month_start=timezone.localdate().replace(day=1),
        page_views=10,
        unique_visitors=4,
    )
    for dry_run in [True, False, False]:
        result = aggregate_and_cleanup_page_views(dry_run=dry_run)
        assert result["deleted_events"] == 0 and result["retained_events"] == 1
        assert PageViewEvent.objects.count() == 1
        old.refresh_from_db()
        assert old.page_views == 10 and old.unique_visitors == 4


@pytest.mark.django_db
def test_existing_maintenance_command_remains_safe_and_compatible():
    out = StringIO()
    call_command("cleanup_analytics_retention", "--dry-run", stdout=out)
    assert json.loads(out.getvalue())["policy"] == "preserve_exact_history"

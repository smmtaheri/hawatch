"""Keep exact event history for arbitrary rolling attribution windows.

The maintenance entry point remains compatible with existing deployments.
Legacy monthly totals remain immutable; they cannot restore deleted events.
"""

from .models import PageViewEvent


def aggregate_and_cleanup_page_views(*, dry_run: bool = False) -> dict:
    return {
        "dry_run": dry_run,
        "policy": "preserve_exact_history",
        "retained_events": PageViewEvent.objects.count(),
        "deleted_events": 0,
        "aggregate_groups": 0,
        "aggregate_page_views": 0,
        "aggregate_unique_visitors": 0,
    }

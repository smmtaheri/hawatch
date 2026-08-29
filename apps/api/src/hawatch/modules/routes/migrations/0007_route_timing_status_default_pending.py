# Safe default change + demote incomplete estimated/curated rows only.

from django.db import migrations, models


USABLE_TIMING_STATUSES = frozenset({"estimated", "curated"})


def _route_timing_complete(*, timing_status, one_way_minutes, points) -> bool:
    """Mirror of hawatch.modules.routes.timing.route_timing_complete for migration safety."""
    if timing_status not in USABLE_TIMING_STATUSES:
        return False
    if one_way_minutes is None or int(one_way_minutes) <= 0:
        return False
    ordered = sorted(points, key=lambda point: point.sort_order)
    if len(ordered) < 2:
        return False
    cumulatives = []
    for point in ordered:
        if point.timing_status not in USABLE_TIMING_STATUSES:
            return False
        if point.cumulative_minutes is None:
            return False
        cumulatives.append(int(point.cumulative_minutes))
    if cumulatives[0] != 0:
        return False
    for previous, current in zip(cumulatives, cumulatives[1:]):
        if current <= previous:
            return False
    if cumulatives[-1] != int(one_way_minutes):
        return False
    return True


def demote_incomplete_timing(apps, schema_editor):
    """Pending for incomplete timing; leave complete estimated/curated alone."""
    Route = apps.get_model("routes", "Route")
    RoutePoint = apps.get_model("routes", "RoutePoint")
    for route in Route.objects.exclude(timing_status="pending").iterator():
        points = list(RoutePoint.objects.filter(route_id=route.pk))
        complete = _route_timing_complete(
            timing_status=route.timing_status,
            one_way_minutes=route.one_way_minutes,
            points=points,
        )
        if not complete:
            route.timing_status = "pending"
            route.save(update_fields=["timing_status"])


class Migration(migrations.Migration):
    dependencies = [
        ("routes", "0006_route_timing_provenance"),
    ]

    operations = [
        migrations.AlterField(
            model_name="route",
            name="timing_status",
            field=models.CharField(
                choices=[("curated", "curated"), ("estimated", "estimated"), ("pending", "pending")],
                default="pending",
                max_length=16,
            ),
        ),
        migrations.RunPython(demote_incomplete_timing, migrations.RunPython.noop),
    ]

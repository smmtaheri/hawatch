"""Apply offline route metrics; never reads GPX or calls a provider."""
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from hawatch.modules.routes.models import Route
from hawatch.api.v1.week_cache import invalidate_week_cache


class Command(BaseCommand):
    help = "Apply reviewed route metrics for matching canonical point chains."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report changes without writing to the database.",
        )

    def handle(self, *args, **options):
        document = json.loads(
            (settings.FIXTURES_DIR / "route_descent_v1.json").read_text()
        )
        if document["schema_version"] not in ("route-descent-1", "route-metrics-2"):
            raise CommandError("Unknown route metrics schema")

        dry_run = options["dry_run"]
        updated_routes = 0
        updated_points = 0
        skipped = 0
        unchanged = 0
        with transaction.atomic():
            for item in document["routes"]:
                route = Route.objects.filter(slug=item["slug"]).first()
                points = (
                    list(
                        route.points.select_related("weather_point").order_by(
                            "sort_order", "pk"
                        )
                    )
                    if route
                    else []
                )
                chain = [
                    point.weather_point.slug if point.weather_point else None
                    for point in points
                ]
                if route is None or chain != item["chain"]:
                    skipped += 1
                    continue

                if "descent_m" not in item and not item.get(
                    "cumulative_distance_m"
                ) and not item.get("segment_distance_m"):
                    raise CommandError(
                        f"{route.slug}: no descent or segment-distance data"
                    )

                descent = item.get("descent_m")
                evidence = dict(route.descent_evidence or {})
                if descent is not None:
                    if type(descent) is not int or descent < 0:
                        raise CommandError(f"{route.slug}: invalid descent")
                    descent_evidence = item.get("evidence")
                    if not isinstance(descent_evidence, dict) or not descent_evidence:
                        raise CommandError(f"{route.slug}: descent evidence required")
                    evidence = dict(descent_evidence)

                cumulative = item.get("cumulative_distance_m")
                segment_distances = item.get("segment_distance_m")
                if cumulative is not None and segment_distances is not None:
                    raise CommandError(
                        f"{route.slug}: specify cumulative or segment distances, not both"
                    )
                if cumulative is not None:
                    if (
                        len(cumulative) != len(points)
                        or cumulative[0] != 0
                        or any(type(value) is not int for value in cumulative)
                        or any(b <= a for a, b in zip(cumulative, cumulative[1:]))
                    ):
                        raise CommandError(f"{route.slug}: invalid cumulative distances")
                    segment_distances = [
                        0,
                        *[
                            end - start
                            for start, end in zip(cumulative, cumulative[1:])
                        ],
                    ]

                point_updates = []
                if segment_distances is not None:
                    if (
                        len(segment_distances) != len(points)
                        or segment_distances[0] != 0
                        or any(type(value) is not int or value < 0 for value in segment_distances)
                    ):
                        raise CommandError(f"{route.slug}: invalid segment distances")
                    for point, distance in zip(points, segment_distances):
                        # Never replace a previously curated or GPX-derived value.
                        if point.segment_distance_m is None:
                            point.segment_distance_m = distance
                            point_updates.append(point)

                distance_evidence = item.get("segment_distance_evidence")
                if distance_evidence is not None:
                    if not isinstance(distance_evidence, dict) or not distance_evidence:
                        raise CommandError(
                            f"{route.slug}: invalid segment-distance evidence"
                        )
                    evidence["segment_distance_estimate"] = distance_evidence

                # Compare the final combined evidence once. Comparing the base
                # descent evidence before adding distance evidence marks every
                # unchanged reapplication as a write and invalidates weather.
                changed = route.descent_evidence != evidence
                if descent is not None and route.descent_m != descent:
                    route.descent_m = descent
                    changed = True
                if changed:
                    route.descent_evidence = evidence

                if point_updates and not dry_run:
                    type(points[0]).objects.bulk_update(
                        point_updates, ["segment_distance_m"]
                    )
                updated_points += len(point_updates)

                if changed:
                    updated_routes += 1
                    if not dry_run:
                        route.save(update_fields=["descent_m", "descent_evidence"])
                else:
                    unchanged += 1

            if (updated_routes or updated_points) and not dry_run:
                invalidate_week_cache()

        mode = "Would update" if dry_run else "Updated"
        self.stdout.write(
            f"{mode} routes: {updated_routes}; segment distances: {updated_points}; "
            f"unchanged routes: {unchanged}; unmatched routes: {skipped}; "
            f"unresolved routes: {len(document.get('unresolved', []))}"
        )

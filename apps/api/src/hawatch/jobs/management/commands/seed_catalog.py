from django.core.management.base import BaseCommand

from hawatch.modules.catalog.catalog import DEFAULT_CATALOG_FILE, seed_catalog


class Command(BaseCommand):
    help = (
        "Idempotently import a versioned destination catalog from JSON. "
        "Non-destructive by default; use --prune only for intentional fixture cleanup."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=DEFAULT_CATALOG_FILE,
            help="Path relative to apps/api/fixtures, for example catalog/tochal_v1.json.",
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            help="Remove fixture_managed rows for this destination that are absent from the JSON.",
        )

        parser.add_argument(
            "--force-adopt",
            action="store_true",
            help="Overwrite operator-managed rows that collide on slug. Default is skip+report.",
        )

    def handle(self, *args, **options):
        result = seed_catalog(
            catalog_file=options["file"],
            prune=options["prune"],
            force_adopt=options["force_adopt"],
        )
        if result.get("conflicts"):
            for item in result["conflicts"]:
                self.stdout.write(self.style.WARNING(f"Conflict: {item}"))
        self.stdout.write(
            self.style.SUCCESS(
                "Catalog {version}: {points} weather points, {routes} routes for {destination} "
                "(pruned_routes={pruned_routes}, pruned_points={pruned_points}).".format(
                    version=result["catalog_version"],
                    points=result["weather_point_count"],
                    routes=result["route_count"],
                    destination=result["destination"],
                    pruned_routes=result.get("pruned_routes", 0),
                    pruned_points=result.get("pruned_points", 0),
                )
            )
        )

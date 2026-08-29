from django.core.management.base import BaseCommand

from hawatch.modules.catalog.tochal import seed_tochal_catalog


class Command(BaseCommand):
    help = (
        "Idempotently import the versioned Tochal catalog (non-destructive by default). "
        "Prefer bootstrap_live_catalog_if_empty at production startup."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--prune",
            action="store_true",
            help="Remove fixture_managed Tochal rows absent from the JSON. Never automatic at startup.",
        )
        parser.add_argument(
            "--force-adopt",
            action="store_true",
            help="Overwrite operator-managed rows that collide on slug. Default is skip+report.",
        )

    def handle(self, *args, **options):
        result = seed_tochal_catalog(prune=options["prune"], force_adopt=options["force_adopt"])
        if result.get("conflicts"):
            for item in result["conflicts"]:
                self.stdout.write(self.style.WARNING(f"Conflict: {item}"))
        self.stdout.write(
            self.style.SUCCESS(
                "Tochal catalog {version}: {points} weather points, {routes} routes "
                "(pruned_routes={pruned_routes}, pruned_points={pruned_points}).".format(
                    version=result["catalog_version"],
                    points=result["weather_point_count"],
                    routes=result["route_count"],
                    pruned_routes=result.get("pruned_routes", 0),
                    pruned_points=result.get("pruned_points", 0),
                )
            )
        )

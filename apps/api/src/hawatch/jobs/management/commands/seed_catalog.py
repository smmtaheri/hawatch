from django.core.management.base import BaseCommand

from hawatch.modules.catalog.catalog import DEFAULT_CATALOG_FILE, seed_catalog


class Command(BaseCommand):
    help = "Idempotently seed a versioned Hawatch destination catalog from a JSON fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=DEFAULT_CATALOG_FILE,
            help="Path relative to apps/api/fixtures, for example catalog/tochal_v1.json.",
        )

    def handle(self, *args, **options):
        result = seed_catalog(catalog_file=options["file"])
        self.stdout.write(
            self.style.SUCCESS(
                "Catalog {version}: {points} weather points, {routes} routes for {destination}.".format(
                    version=result["catalog_version"],
                    points=result["weather_point_count"],
                    routes=result["route_count"],
                    destination=result["destination"],
                )
            )
        )

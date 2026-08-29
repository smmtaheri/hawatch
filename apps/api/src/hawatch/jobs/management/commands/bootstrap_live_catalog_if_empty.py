from django.core.management.base import BaseCommand

from hawatch.modules.catalog.catalog import DEFAULT_CATALOG_FILE, bootstrap_live_catalog_if_empty


class Command(BaseCommand):
    help = (
        "Bootstrap the packaged live catalog only when the database has no live WeatherPoints. "
        "Never prunes. Safe for production API restart."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=DEFAULT_CATALOG_FILE,
            help="Path relative to apps/api/fixtures used when the live catalog is empty.",
        )

    def handle(self, *args, **options):
        result = bootstrap_live_catalog_if_empty(catalog_file=options["file"])
        if result is None:
            self.stdout.write("Live catalog already present; bootstrap skipped.")
            return
        self.stdout.write(
            self.style.SUCCESS(
                "Bootstrapped catalog {version}: {points} weather points, {routes} routes.".format(
                    version=result["catalog_version"],
                    points=result["weather_point_count"],
                    routes=result["route_count"],
                )
            )
        )

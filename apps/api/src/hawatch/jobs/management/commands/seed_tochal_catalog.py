from django.core.management.base import BaseCommand

from hawatch.modules.catalog.tochal import seed_tochal_catalog


class Command(BaseCommand):
    help = "Idempotently seed the versioned Tochal weather-point catalog and five routes."

    def handle(self, *args, **options):
        result = seed_tochal_catalog()
        self.stdout.write(
            self.style.SUCCESS(
                "Tochal catalog {version}: {points} weather points, {routes} routes.".format(
                    version=result["catalog_version"],
                    points=result["weather_point_count"],
                    routes=result["route_count"],
                )
            )
        )

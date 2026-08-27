from django.core.management.base import BaseCommand

from hawatch.integrations.weather.ingest import ingest_catalog
from hawatch.integrations.weather.providers.open_meteo import OpenMeteoProvider
from hawatch.modules.catalog.catalog import DEFAULT_CATALOG_FILE, load_catalog_file, seed_catalog


class Command(BaseCommand):
    help = "Ingest Open-Meteo forecasts for a versioned catalog (never called by API handlers)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed-catalog",
            action="store_true",
            help="Seed the selected JSON catalog before ingestion.",
        )
        parser.add_argument(
            "--catalog",
            default=DEFAULT_CATALOG_FILE,
            help="Path relative to apps/api/fixtures, for example catalog/tochal_v1.json.",
        )
        parser.add_argument("--batch-size", type=int, default=None)
        parser.add_argument("--forecast-days", type=int, default=None)

    def handle(self, *args, **options):
        if options["seed_catalog"]:
            result = seed_catalog(catalog_file=options["catalog"])
            self.stdout.write(f"Catalog ready: {result['catalog_version']}")

        catalog_version = load_catalog_file(options["catalog"])["catalog_version"]

        provider = OpenMeteoProvider(
            batch_size=options["batch_size"],
            forecast_days=options["forecast_days"],
        )
        snapshot = ingest_catalog(catalog_version, provider=provider)
        self.stdout.write(
            self.style.SUCCESS(
                "Ingest snapshot {id}: status={status} freshness={freshness} points={points} checksum={checksum}".format(
                    id=snapshot.pk,
                    status=snapshot.status,
                    freshness=snapshot.freshness,
                    points=snapshot.point_count,
                    checksum=snapshot.checksum[:12],
                )
            )
        )

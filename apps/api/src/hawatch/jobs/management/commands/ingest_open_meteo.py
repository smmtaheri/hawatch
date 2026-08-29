from django.core.management.base import BaseCommand

from hawatch.integrations.weather.ingest import ingest_active_catalog, ingest_catalog
from hawatch.integrations.weather.providers.open_meteo import OpenMeteoProvider
from hawatch.modules.catalog.catalog import DEFAULT_CATALOG_FILE, load_catalog_file, seed_catalog


class Command(BaseCommand):
    help = (
        "Ingest Open-Meteo forecasts for active database WeatherPoints "
        "(never called by API handlers)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed-catalog",
            action="store_true",
            help="Optionally import a JSON catalog before ingestion (non-destructive unless --prune).",
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            help="With --seed-catalog, remove fixture_managed rows absent from the JSON. Never automatic.",
        )
        parser.add_argument(
            "--catalog",
            default=DEFAULT_CATALOG_FILE,
            help="Path relative to apps/api/fixtures, for example catalog/tochal_v1.json (seed only).",
        )
        parser.add_argument(
            "--slugs",
            default="",
            help="Comma-separated WeatherPoint slugs to ingest immediately (targeted; no service restart).",
        )
        parser.add_argument(
            "--fixture-version",
            action="store_true",
            help="Legacy: filter ingest by the JSON catalog_version instead of active DB selection.",
        )
        parser.add_argument("--batch-size", type=int, default=None)
        parser.add_argument("--forecast-days", type=int, default=None)

    def handle(self, *args, **options):
        if options["seed_catalog"]:
            result = seed_catalog(catalog_file=options["catalog"], prune=options["prune"])
            self.stdout.write(
                f"Catalog ready: {result['catalog_version']} "
                f"(pruned={result.get('pruned', False)})"
            )

        provider = OpenMeteoProvider(
            batch_size=options["batch_size"],
            forecast_days=options["forecast_days"],
        )
        slug_text = (options["slugs"] or "").strip()
        slugs = [item.strip() for item in slug_text.split(",") if item.strip()] or None

        if options["fixture_version"]:
            catalog_version = load_catalog_file(options["catalog"])["catalog_version"]
            snapshot = ingest_catalog(catalog_version, provider=provider)
        else:
            snapshot = ingest_active_catalog(provider=provider, slugs=slugs)

        self.stdout.write(
            self.style.SUCCESS(
                "Ingest snapshot {id}: status={status} freshness={freshness} points={points} "
                "catalog={catalog} checksum={checksum}".format(
                    id=snapshot.pk,
                    status=snapshot.status,
                    freshness=snapshot.freshness,
                    points=snapshot.point_count,
                    catalog=snapshot.catalog_version,
                    checksum=snapshot.checksum[:12],
                )
            )
        )

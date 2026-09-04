from django.core.management.base import BaseCommand, CommandError

from hawatch.modules.catalog.catalog import DEFAULT_CATALOG_FILE, bootstrap_live_catalog_if_empty


class Command(BaseCommand):
    help = (
        "Bootstrap packaged live catalog data only when the database has no live WeatherPoints. "
        "Use --all for the complete versioned catalog set; safe for production API restart."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=DEFAULT_CATALOG_FILE,
            help="Path relative to apps/api/fixtures used when the live catalog is empty.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Import all packaged catalogs atomically instead of only --file.",
        )

    def handle(self, *args, **options):
        if options["all"]:
            from hawatch.modules.catalog.runtime import live_catalog_is_empty
            from hawatch.modules.catalog.sync import apply_sync, build_sync_plan, load_packaged_catalogs

            if not live_catalog_is_empty():
                self.stdout.write("Live catalog already present; bootstrap skipped.")
                return
            try:
                desired = load_packaged_catalogs()
                plan = build_sync_plan(desired)
                if plan["conflicted"]:
                    raise CommandError("Catalog bootstrap blocked by conflicts:\n- " + "\n- ".join(plan["conflicted"]))
                counts = apply_sync(desired, plan)
            except (OSError, TypeError, ValueError) as exc:
                raise CommandError(f"Could not bootstrap all catalogs: {exc}") from exc
            self.stdout.write(
                self.style.SUCCESS(
                    "Bootstrapped all catalogs: created={created}, updated={updated}, "
                    "unchanged={unchanged}, deactivated={deactivated}, deleted={deleted}.".format(**counts)
                )
            )
            return

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

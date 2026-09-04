import json

from django.core.management.base import BaseCommand, CommandError

from hawatch.modules.catalog.preflight import run_catalog_preflight


class Command(BaseCommand):
    help = "Run read-only readiness checks for the live database catalog and stored provider resolutions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--point",
            dest="point",
            default="",
            help="Limit checks to one point slug; default checks all active live points.",
        )
        parser.add_argument(
            "--require-forecast",
            action="store_true",
            help="Treat missing/stale provider data as errors; use after a targeted ingest.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Treat warnings as failures too.",
        )
        parser.add_argument("--json", action="store_true", dest="as_json", help="Print the full JSON report.")

    def handle(self, *args, **options):
        report = run_catalog_preflight(
            point_slug=options["point"].strip() or None,
            require_forecast=options["require_forecast"],
            strict=options["strict"],
        )
        if options["as_json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            summary = report["summary"]
            self.stdout.write(
                "catalog preflight: points={point_count} routes={route_count} "
                "ingestible_points={ingestible_point_count} provider_checked={provider_checked_point_count} "
                "timed_routes={timed_route_count} errors={error_count} warnings={warning_count} pass={pass}".format(
                    **summary
                )
            )
            for entry in report["errors"]:
                self.stdout.write(self.style.ERROR(f"ERROR: {entry}"))
            for entry in report["warnings"]:
                self.stdout.write(self.style.WARNING(f"WARNING: {entry}"))

        if not report["summary"]["pass"]:
            raise CommandError("Catalog preflight failed; inspect the errors/warnings above.")

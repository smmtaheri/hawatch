import json
import sys

from django.core.management.base import BaseCommand, CommandError

from hawatch.modules.catalog.catalog import (
    DEFAULT_CATALOG_FILE,
    CatalogImportConflict,
    load_catalog_file,
    _validate_document_shape,
    seed_catalog,
)


class Command(BaseCommand):
    help = (
        "Idempotently import a versioned point catalog from JSON. "
        "Non-destructive by default; use --prune only for intentional fixture cleanup."
    )

    def add_arguments(self, parser):
        input_group = parser.add_mutually_exclusive_group()
        input_group.add_argument(
            "--file",
            default=DEFAULT_CATALOG_FILE,
            help="Path relative to apps/api/fixtures, for example catalog/tochal_v1.json.",
        )
        input_group.add_argument(
            "--stdin",
            action="store_true",
            help="Read one catalog JSON document from stdin; useful for DB-only updates without shipping the file.",
        )
        parser.add_argument(
            "--check-only",
            action="store_true",
            help="Validate the input shape and exit without changing the database.",
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            help="Remove fixture_managed rows for this point catalog that are absent from the JSON.",
        )

        parser.add_argument(
            "--force-adopt",
            action="store_true",
            help="Overwrite operator-managed rows that collide on slug. Default is skip+report.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail and roll back when an operator-managed slug conflict is found.",
        )

    def handle(self, *args, **options):
        if options["stdin"]:
            try:
                catalog = json.load(sys.stdin)
            except (json.JSONDecodeError, TypeError) as exc:
                raise CommandError(f"Invalid catalog JSON on stdin: {exc}") from exc
            source = "stdin"
        else:
            catalog = None
            source = options["file"]

        try:
            if catalog is not None:
                _validate_document_shape(catalog)
            if options["check_only"]:
                if catalog is None:
                    catalog = load_catalog_file(options["file"])
                    _validate_document_shape(catalog)
                self.stdout.write(self.style.SUCCESS(f"Catalog input is valid ({source}). No database changes made."))
                return
            result = seed_catalog(
                catalog=catalog,
                catalog_file=None if catalog is not None else options["file"],
                prune=options["prune"],
                force_adopt=options["force_adopt"],
                raise_on_conflict=options["strict"],
            )
        except CatalogImportConflict as exc:
            raise CommandError("Catalog import conflicts; no changes were kept:\n- " + "\n- ".join(exc.conflicts)) from exc
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise CommandError(f"Catalog import failed: {exc}") from exc
        if result.get("conflicts"):
            for item in result["conflicts"]:
                self.stdout.write(self.style.WARNING(f"Conflict: {item}"))
        self.stdout.write(
            self.style.SUCCESS(
                "Catalog {version}: {points} weather points, {routes} routes for {point}.".format(
                    version=result["catalog_version"],
                    points=result["weather_point_count"],
                    routes=result["route_count"],
                    point=result["point"],
                )
            )
        )

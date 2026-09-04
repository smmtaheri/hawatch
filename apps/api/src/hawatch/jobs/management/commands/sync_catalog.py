from django.core.management.base import BaseCommand, CommandError

from hawatch.modules.catalog.catalog import CatalogImportConflict
from hawatch.modules.catalog.sync import apply_sync, build_sync_plan, load_packaged_catalogs


class Command(BaseCommand):
    help = "Synchronize all packaged catalogs into the existing database (dry-run by default)."

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--dry-run", action="store_true", help="Show the sync plan without changing the database (default).")
        mode.add_argument("--apply", action="store_true", help="Apply the sync atomically; required for database changes.")

    def handle(self, *args, **options):
        try:
            desired = load_packaged_catalogs()
            plan = build_sync_plan(desired)
        except (OSError, TypeError, ValueError) as exc:
            raise CommandError(f"Could not build catalog sync plan: {exc}") from exc

        self._print_plan(plan)
        if plan["conflicted"]:
            raise CommandError("Catalog sync blocked by conflicts; no database changes were made.")
        if not options["apply"]:
            self.stdout.write(self.style.SUCCESS("Dry-run complete; no database changes made. Pass --apply to execute."))
            return

        try:
            counts = apply_sync(desired, plan)
        except CatalogImportConflict as exc:
            raise CommandError("Catalog sync conflicts; no changes were kept:\n- " + "\n- ".join(exc.conflicts)) from exc
        except (ValueError, OSError, TypeError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                "Catalog sync applied: created={created}, updated={updated}, unchanged={unchanged}, "
                "deactivated={deactivated}, deleted={deleted}, skipped={skipped}, conflicted={conflicted}.".format(**counts)
            )
        )

    def _print_plan(self, plan: dict):
        for kind in ("points", "routes"):
            counts = plan[kind]
            self.stdout.write(
                f"{kind}: created={len(counts['created'])}, updated={len(counts['updated'])}, "
                f"unchanged={len(counts['unchanged'])}"
            )
            for label in ("created", "updated"):
                for slug in counts[label]:
                    self.stdout.write(f"  {label}: {kind[:-1]} {slug}")
        for item in plan["stale_routes"]:
            self.stdout.write(self.style.WARNING(f"would deactivate route {item['slug']}: {item['reason']}"))
        for item in plan["stale_points"]:
            self.stdout.write(self.style.WARNING(f"would deactivate point {item['slug']}: {item['reason']}"))
        for item in plan["stale_route_points"]:
            self.stdout.write(self.style.WARNING(f"would delete RoutePoint {item['route']}:{item['slug']}: {item['reason']}"))
        for item in plan["skipped"]:
            self.stdout.write(self.style.WARNING(f"skipped: {item}"))
        for item in plan["conflicted"]:
            self.stdout.write(self.style.ERROR(f"conflict: {item}"))
        self.stdout.write(
            "plan summary: deactivated={}, deleted={}, skipped={}, conflicted={}".format(
                len(plan["stale_points"]) + len(plan["stale_routes"]),
                len(plan["stale_route_points"]),
                len(plan["skipped"]),
                len(plan["conflicted"]),
            )
        )

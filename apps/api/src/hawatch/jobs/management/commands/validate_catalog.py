import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hawatch.modules.catalog.validation import (
    format_issues,
    validate_catalog_document,
    validate_database_catalog,
)


class Command(BaseCommand):
    help = "Validate catalog identity, route references and optional current DB state without changing data."

    def add_arguments(self, parser):
        parser.add_argument("--file", help="Catalog path relative to fixtures; defaults to every catalog/*.json.")
        parser.add_argument("--all", action="store_true", help="Validate every checked-in catalog fixture (default when --file is omitted).")
        parser.add_argument("--database", action="store_true", help="Also validate the current database catalog.")
        parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")

    def handle(self, *args, **options):
        if options["file"] and options["all"]:
            raise CommandError("Use either --file or --all, not both.")
        fixtures = Path(settings.FIXTURES_DIR).resolve()
        paths = [fixtures / options["file"]] if options["file"] else sorted((fixtures / "catalog").glob("*.json"))
        issues = []
        for path in paths:
            if fixtures not in path.resolve().parents or not path.is_file():
                raise CommandError(f"Catalog file does not exist inside fixtures: {path}")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise CommandError(f"Could not read catalog {path}: {exc}") from exc
            file_issues = validate_catalog_document(data)
            issues.extend(file_issues)
            self.stdout.write(f"{path.relative_to(fixtures)}: points={len(data.get('weather_points', {}))} routes={len(data.get('routes', {}))}")
        if options["database"]:
            db_issues = validate_database_catalog(strict=options["strict"])
            issues.extend(db_issues)
        if issues:
            self.stdout.write(format_issues(issues))
        errors = [issue for issue in issues if issue.level == "error" or (options["strict"] and issue.level == "warning")]
        if errors:
            raise CommandError(f"Catalog validation failed with {len(errors)} issue(s).")
        self.stdout.write(self.style.SUCCESS("Catalog validation passed."))

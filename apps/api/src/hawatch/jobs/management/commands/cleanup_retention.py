import json

from django.core.management.base import BaseCommand, CommandError

from hawatch.jobs.retention import run_retention


class Command(BaseCommand):
    help = "Delete Hawatch forecast, rotated log and OpenSearch data older than seven days."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7, help="Retention window; maximum is seven days.")
        parser.add_argument("--dry-run", action="store_true", help="Report deletions without deleting anything.")
        parser.add_argument("--skip-opensearch", action="store_true", help="Skip OpenSearch index retention.")

    def handle(self, *args, **options):
        try:
            result = run_retention(
                days=options["days"],
                dry_run=options["dry_run"],
                skip_opensearch=options["skip_opensearch"],
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))

import json

from django.core.management.base import BaseCommand, CommandError

from hawatch.modules.analytics.retention import aggregate_and_cleanup_page_views


class Command(BaseCommand):
    help = "Report retained exact analytics history; historical monthly totals remain unchanged."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the non-destructive history retention policy.",
        )

    def handle(self, *args, **options):
        try:
            result = aggregate_and_cleanup_page_views(dry_run=options["dry_run"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))

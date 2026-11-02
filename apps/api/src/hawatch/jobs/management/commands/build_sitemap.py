import time

from django.core.management.base import BaseCommand, CommandError

from hawatch.modules.catalog.sitemap import publish_sitemap


class Command(BaseCommand):
    help = "Build and atomically publish a validated, persistent sitemap (no provider calls)."

    def add_arguments(self, parser):
        parser.add_argument("--wait-lock-seconds", type=float, default=0)

    def handle(self, *args, **options):
        wait = options["wait_lock_seconds"]
        if wait < 0:
            raise CommandError("--wait-lock-seconds must be nonnegative")
        deadline = time.monotonic() + wait
        try:
            while True:
                result = publish_sitemap()
                if result["status"] != "busy" or time.monotonic() >= deadline:
                    break
                time.sleep(0.1)
        except Exception as exc:
            raise CommandError(f"Sitemap generation failed ({type(exc).__name__}); previous XML retained") from exc
        if result["status"] == "busy":
            raise CommandError("Another sitemap builder is running; retry after it completes")
        self.stdout.write(f"Sitemap ready: urls={result['counts']['urls']} changed={result['changed']} sha256={result['sha256'][:12]}")

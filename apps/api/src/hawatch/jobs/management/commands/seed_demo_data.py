from django.core.management.base import BaseCommand
from django.conf import settings

from hawatch.modules.catalog.seed import seed_demo_data


class Command(BaseCommand):
    help = "Idempotently seed Hawatch demo destinations, routes, points, and forecasts."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Regenerate forecasts even if the hour bucket is unchanged.")

    def handle(self, *args, **options):
        if not settings.DEMO_DATA_ENABLED:
            self.stdout.write("DEMO_DATA_ENABLED is false; catalog/forecast seed skipped.")
            return
        state = seed_demo_data(force=options["force"])
        if state is None:
            self.stdout.write("No demo state to report.")
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo seed {settings.DEMO_SEED_VERSION} ready for bucket {state.last_hour_bucket}."
            )
        )

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hawatch.modules.destinations.models import Destination

MAX_POPULAR_DESTINATIONS = 4


class Command(BaseCommand):
    help = "Set the ordered home-page popular destinations; all other destinations become non-popular."

    def add_arguments(self, parser):
        parser.add_argument(
            "destination_slugs",
            nargs="*",
            metavar="SLUG",
            help="Destination slugs in display order (maximum four).",
        )
        parser.add_argument(
            "--slugs",
            dest="slugs_csv",
            default="",
            help="Comma-separated destination slugs in display order.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove all destinations from the home-page popular set.",
        )

    def handle(self, *args, **options):
        positional = [slug.strip() for slug in options["destination_slugs"] if slug.strip()]
        csv_slugs = [slug.strip() for slug in options["slugs_csv"].split(",") if slug.strip()]
        if positional and csv_slugs:
            raise CommandError("Use positional slugs or --slugs, not both.")
        if options["clear"] and (positional or csv_slugs):
            raise CommandError("--clear cannot be combined with destination slugs.")

        slugs = [] if options["clear"] else (positional or csv_slugs)
        if not slugs and not options["clear"]:
            raise CommandError("Provide at least one destination slug, or use --clear.")
        if len(slugs) > MAX_POPULAR_DESTINATIONS:
            raise CommandError(f"At most {MAX_POPULAR_DESTINATIONS} popular destinations are supported.")
        if len(slugs) != len(set(slugs)):
            raise CommandError("Destination slugs must be unique.")

        selected = list(Destination.objects.filter(slug__in=slugs, is_active=True))
        selected_by_slug = {destination.slug: destination for destination in selected}
        missing = [slug for slug in slugs if slug not in selected_by_slug]
        if missing:
            raise CommandError(f"Unknown or inactive destination slug(s): {', '.join(missing)}")

        with transaction.atomic():
            Destination.objects.update(is_popular=False, popular_order=0)
            for order, slug in enumerate(slugs, start=1):
                Destination.objects.filter(pk=selected_by_slug[slug].pk).update(
                    is_popular=True,
                    popular_order=order,
                )

        if slugs:
            self.stdout.write(
                self.style.SUCCESS(
                    "Popular destinations set: "
                    + " → ".join(f"{order}. {slug}" for order, slug in enumerate(slugs, start=1))
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Popular destinations cleared."))

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hawatch.modules.forecasts.models import WeatherPoint

MAX_POPULAR_POINTS = 4


class Command(BaseCommand):
    help = "Set the ordered home-page popular points."

    def add_arguments(self, parser):
        parser.add_argument("point_slugs", nargs="*", metavar="SLUG")
        parser.add_argument("--slugs", dest="slugs_csv", default="")
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        positional = [slug.strip() for slug in options["point_slugs"] if slug.strip()]
        csv_slugs = [slug.strip() for slug in options["slugs_csv"].split(",") if slug.strip()]
        if positional and csv_slugs:
            raise CommandError("Use positional slugs or --slugs, not both.")
        if options["clear"] and (positional or csv_slugs):
            raise CommandError("--clear cannot be combined with point slugs.")
        slugs = [] if options["clear"] else (positional or csv_slugs)
        if not slugs and not options["clear"]:
            raise CommandError("Provide at least one point slug, or use --clear.")
        if len(slugs) > MAX_POPULAR_POINTS or len(slugs) != len(set(slugs)):
            raise CommandError(f"Provide at most {MAX_POPULAR_POINTS} unique point slugs.")
        selected = {point.slug: point for point in WeatherPoint.objects.filter(slug__in=slugs, is_active=True)}
        missing = [slug for slug in slugs if slug not in selected]
        if missing:
            raise CommandError(f"Unknown or inactive point slug(s): {', '.join(missing)}")
        with transaction.atomic():
            WeatherPoint.objects.update(is_popular=False, popular_order=0)
            for order, slug in enumerate(slugs, start=1):
                WeatherPoint.objects.filter(pk=selected[slug].pk).update(is_popular=True, popular_order=order)
        self.stdout.write(self.style.SUCCESS("Popular points updated."))
